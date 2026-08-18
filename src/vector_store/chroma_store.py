"""ChromaDB çok kiracılı vektör deposu."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """
    Her vektörde zorunlu company_id metadata'sı ile izole arama sağlar.
    """

    def __init__(
        self,
        persist_directory: Path,
        collection_name: str,
        company_id: str,
    ) -> None:
        self._company_id = company_id
        self._client = chromadb.PersistentClient(
            path=str(persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB koleksiyonu hazır | firma: %s | kayıt: %d",
            company_id,
            self._collection.count(),
        )

    @property
    def company_id(self) -> str:
        return self._company_id

    def _tenant_filter(self) -> Dict[str, str]:
        """Tüm sorgularda kullanılacak kiracı filtresi."""
        return {"company_id": self._company_id}

    def add_embeddings(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        extra_metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """
        Vektörleri company_id ile birlikte kaydeder.
        Aynı id varsa upsert davranışı için önce silinir.
        """
        if not ids:
            return 0

        metadatas: List[Dict[str, Any]] = []
        for i, doc_id in enumerate(ids):
            meta: Dict[str, Any] = {"company_id": self._company_id}
            if extra_metadata and i < len(extra_metadata):
                meta.update(extra_metadata[i])
            metadatas.append(meta)

        try:
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as exc:
            logger.error("ChromaDB upsert hatası: %s", exc)
            raise

        return len(ids)

    def query_similar(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        min_similarity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Yalnızca bu kiracının (company_id) vektörleri arasında benzerlik arar.

        Chroma cosine space: similarity = 1 - distance (L2-normalize vektörlerde).
        min_similarity verilirse eşiğin altındaki sonuçlar elenir.
        """
        fetch_k = n_results
        if min_similarity is not None:
            fetch_k = max(n_results * 3, n_results + 5)

        raw = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_k,
            where=self._tenant_filter(),
        )

        if min_similarity is None:
            return raw

        filtered: Dict[str, List] = {"ids": [[]], "distances": [[]], "metadatas": [[]]}
        meta_list = raw.get("metadatas", [[]])[0] or []
        for i, (doc_id, dist) in enumerate(zip(raw["ids"][0], raw["distances"][0])):
            similarity = 1.0 - dist
            if similarity < min_similarity:
                continue
            filtered["ids"][0].append(doc_id)
            filtered["distances"][0].append(dist)
            if i < len(meta_list):
                filtered["metadatas"][0].append(meta_list[i])
            if len(filtered["ids"][0]) >= n_results:
                break

        return filtered

    def count_for_tenant(self) -> int:
        """Bu kiracıya ait kayıt sayısını döner."""
        result = self._collection.get(where=self._tenant_filter())
        return len(result["ids"]) if result["ids"] else 0

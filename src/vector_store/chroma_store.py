import chromadb

from src.config import CHROMA_PERSIST_DIR, LIVE_CLIP_COLLECTION_NAME


class FashionVectorStore:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        self.collection = self.client.get_or_create_collection(
            name=LIVE_CLIP_COLLECTION_NAME
        )

    def add_vector(
        self,
        product_id: int,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        self.collection.add(
            ids=[str(product_id)],
            embeddings=[embedding],
            metadatas=[metadata],
        )

    def search_similar(
        self,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> dict:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

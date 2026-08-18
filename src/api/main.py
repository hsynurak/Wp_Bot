"""FastAPI Ana Uygulaması (Entrypoint)."""

import time
import httpx
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from src.api.schemas import SearchRequest, SearchResponse, SearchResultItem
from src.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, CLIP_SIMILARITY_THRESHOLD
from src.models.feature_extractor import get_clip_extractor, CLIPExtractor
from src.vector_store.chroma_store import ChromaVectorStore

# Uygulama yaşam döngüsü boyunca modeli bellekte tutacak global sözlük
ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başlarken modeli belleğe alır, kapanırken temizler."""
    print("Modeller yükleniyor... (CLIP)")
    ml_models["extractor"] = get_clip_extractor()
    print("Modeller hazır!")
    yield
    ml_models.clear()

app = FastAPI(
    title="WhatsApp Smart Style Assistant API",
    description="Multi-tenant görsel benzerlik arama motoru.",
    version="1.0.0",
    lifespan=lifespan
)

async def download_image(url: str) -> bytes:
    """Görseli asenkron olarak indirir."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as e:
            raise HTTPException(status_code=400, detail=f"Görsel indirilemedi: {str(e)}")

@app.post("/api/v1/search", response_model=SearchResponse)
async def search_similar_images(request: SearchRequest):
    """Verilen görsel URL'si ile ChromaDB'de company_id bazlı benzerlik araması yapar."""
    start_time = time.time()
    
    # 1. URL'den görseli asenkron olarak belleğe (RAM) indir
    image_bytes = await download_image(str(request.image_url))
        
    try:
        # 2. Vektör Çıkarımı (Geçici dosya YOK, tamamen bellekte!)
        extractor: CLIPExtractor = ml_models["extractor"]
        embeddings, _ = extractor.extract_from_bytes([image_bytes])
        
        if not embeddings:
            raise HTTPException(status_code=422, detail="Görselden vektör çıkarılamadı.")
            
        query_embedding = embeddings[0]
        
        # 3. ChromaDB Sorgusu
        store = ChromaVectorStore(
            persist_directory=CHROMA_PERSIST_DIR,
            collection_name=CHROMA_COLLECTION_NAME,
            company_id=request.company_id
        )
        
        min_sim = request.min_similarity or CLIP_SIMILARITY_THRESHOLD
        raw_results = store.query_similar(
            query_embedding=query_embedding,
            n_results=request.n_results,
            min_similarity=min_sim
        )
        
        # 4. Sonuçları API Şemasına Formatla
        formatted_results = []
        if raw_results and raw_results.get("ids") and raw_results["ids"][0]:
            for i in range(len(raw_results["ids"][0])):
                doc_id = raw_results["ids"][0][i]
                dist = raw_results["distances"][0][i]
                meta = raw_results["metadatas"][0][i] if raw_results.get("metadatas") else {}
                
                formatted_results.append(
                    SearchResultItem(
                        id=doc_id,
                        distance=dist,
                        similarity=1.0 - dist,
                        metadata=meta
                    )
                )
                
        latency = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=formatted_results,
            latency_ms=latency
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sunucu içi hata: {str(e)}")
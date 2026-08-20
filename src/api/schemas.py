"""API İstek ve Yanıt (Request/Response) Modelleri."""

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class SearchRequest(BaseModel):
    """WhatsApp webhook'undan veya uygulamadan gelecek arama isteği."""
    image_url: HttpUrl = Field(..., description="Aranacak görselin URL adresi")
    company_id: str = Field(..., description="Aramanın yapılacağı kiracı/şirket ID'si")
    n_results: int = Field(5, description="Döndürülecek maksimum benzer ürün sayısı")
    min_similarity: Optional[float] = Field(
        None,
        description="Minimum benzerlik eşiği (boş bırakılırsa config.py'deki değer kullanılır)",
    )


class SearchResultItem(BaseModel):
    """Bulunan tek bir ürünün detayları."""
    id: str
    model_code: str
    image_url: Optional[str] = None
    distance: float
    similarity: float


class SearchResponse(BaseModel):
    """Arama ucu noktasının ana yanıt modeli."""
    results: List[SearchResultItem]
    latency_ms: float = Field(..., description="İşlemin milisaniye cinsinden süresi")

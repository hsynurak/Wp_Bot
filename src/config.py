"""Proje genelinde kullanılan sabitler ve yol yapılandırması."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Proje kök dizini (src/ bir üst klasör)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# PyTorch model ağırlıkları proje içinde saklanır
TORCH_HOME = PROJECT_ROOT / ".cache" / "torch"
os.environ.setdefault("TORCH_HOME", str(TORCH_HOME))

PHOTOS_DIR = PROJECT_ROOT / "photos"
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
TEST_SUBSET_DIR = DATA_DIR / "test_subset"
TEST_MANIFEST_PATH = DATA_DIR / "test_subset_manifest.json"
CHROMA_PERSIST_DIR = PROJECT_ROOT / "chroma_db"

# Multi-tenant test kiracısı
DEFAULT_COMPANY_ID = "test_firmasi_1"

# Model ve işleme parametreleri
IMAGE_SIZE = 224
BATCH_SIZE = 32
EMBEDDING_DIM = 512  # CLIP base; large model için 768

# Üretim embedding modeli (şampiyon: CLIP)
EMBEDDING_MODEL = "clip"
CHROMA_COLLECTION_NAME = "collection_clip"

# CLIP — model ve arama parametreleri (buradan özelleştirin)
CLIP_MODEL_ID = "patrickjohncyh/fashion-clip"
# Alternatifler:
#   "openai/clip-vit-large-patch14"     → daha iyi kalite, daha yavaş (dim=768)
#   "patrickjohncyh/fashion-clip"       → moda/tekstil odaklı (dim=512)

CLIP_MODEL_PRESETS: dict[str, dict[str, object]] = {
    "openai/clip-vit-base-patch32": {"dim": 512, "label": "Hızlı, dengeli"},
    "openai/clip-vit-large-patch14": {"dim": 768, "label": "Yüksek kalite"},
    "patrickjohncyh/fashion-clip": {"dim": 512, "label": "Moda/tekstil"},
}

CLIP_NORMALIZE = True          # L2 normalize — cosine benzerliği için önerilir
CLIP_PAD_TO_SQUARE = True      # Ürün kırpılmasın; beyaz pad ile kareye tamamla
CLIP_PAD_COLOR = (255, 255, 255)

# Benzerlik araması (Chroma cosine: similarity = 1 - distance)
CLIP_TOP_K = 10
CLIP_SIMILARITY_THRESHOLD = 0.70  # Altındaki sonuçlar elenir (0.0–1.0)

# Test veri seti
TEST_SUBSET_SIZE = 3000
RANDOM_SEED = 42

# Canlı CLIP vektör koleksiyonu (sprint1_embedding_pipeline_clip.ipynb)
LIVE_CLIP_COLLECTION_NAME = "fashion_clip_products_v1"
TEMP_UPLOADS_DIR = PROJECT_ROOT / "temp_uploads"
BENCHMARK_MODELS: dict[str, str] = {
    "resnet50": "collection_resnet",
    "efficientnet_b0": "collection_efficientnet_b0",
    "efficientnet_b4": "collection_efficientnet_b4",
    "clip": "collection_clip",
}

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:strongpassword123@localhost:5455/fashion_db",
)
MINIO_URL = os.getenv("MINIO_URL", "localhost:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "admin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "strongpassword123")

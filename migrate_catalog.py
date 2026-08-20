import os
import uuid

from pathlib import Path

from tqdm import tqdm
from sqlmodel import Session, select

from src.database import engine
from src.models.db_models import Manufacturers, Base_Products
from src.models import get_extractor
from src.config import PHOTOS_DIR

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MANUFACTURER_NAME = "Katalog Ürünleri"
BATCH_SIZE = 50


def migrate_catalog() -> None:
    with Session(engine) as session:
        manufacturer = session.exec(
            select(Manufacturers).where(Manufacturers.name == MANUFACTURER_NAME)
        ).first()

        if manufacturer is None:
            manufacturer = Manufacturers(name=MANUFACTURER_NAME)
            session.add(manufacturer)
            session.commit()
            session.refresh(manufacturer)

        manufacturer_id = manufacturer.id

    extractor = get_extractor("clip")

    image_paths = [
        p
        for p in PHOTOS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS
    ]

    pending = 0

    with Session(engine) as session:
        for image_path in tqdm(image_paths, desc="Katalog göçü"):
            filename = image_path.name
            model_code = image_path.stem

            existing = session.exec(
                select(Base_Products).where(Base_Products.model_code == model_code)
            ).first()
            if existing is not None:
                continue

            batch, valid_names = extractor.preprocess_paths([image_path])
            if batch.numel() == 0 or not valid_names:
                continue

            embedding = extractor.extract(batch)[0].tolist()

            product = Base_Products(
                model_code=model_code,
                manufacturer_id=manufacturer_id,
                image_url=f"http://localhost:9000/photos/{filename}",
                embedding=embedding,
            )
            session.add(product)
            pending += 1

            if pending >= BATCH_SIZE:
                session.commit()
                pending = 0

        session.commit()


if __name__ == "__main__":
    migrate_catalog()

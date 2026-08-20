import uuid
from sqlmodel import Session
from src.database import engine
from src.models.db_models import Manufacturers, Base_Products

def run_test():
    with Session(engine) as session:
        # 1. Önce bir Üretici (Manufacturer) oluşturalım
        print("1. Üretici oluşturuluyor...")
        new_manufacturer = Manufacturers(
            name="Yapay Zeka Tekstil A.Ş.",
            phone="905550000000",
            email="hello@yztekstil.com"
        )
        session.add(new_manufacturer)
        session.commit()
        session.refresh(new_manufacturer)
        
        # 2. Fashion-CLIP modelinden çıkmış gibi 512 boyutlu sahte bir vektör üretelim
        dummy_embedding = [0.015] * 512
        
        # 3. Ürünümüzü (Base_Product) veritabanına kaydedelim
        print("2. Vektörlü test ürünü kaydediliyor...")
        new_product = Base_Products(
            model_code="KOT-PANT-001",
            manufacturer_id=new_manufacturer.id,
            image_url="http://localhost:9000/photos/kot-pantolon.jpg",
            color="Mavi",
            size="32",
            season="Dört Mevsim",
            embedding=dummy_embedding
        )
        session.add(new_product)
        session.commit()
        
        print("✅ HARİKA! Veriler PostgreSQL'e ve pgvector uzayına başarıyla kaydedildi!")

if __name__ == "__main__":
    run_test()
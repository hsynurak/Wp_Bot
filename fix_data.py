from sqlmodel import Session, select
from sqlalchemy import func
from src.database import engine
from src.models.db_models import Base_Tenants, Base_Products, Base_Subscriptions, Base_Users

with Session(engine) as session:
    # 1. ÇİFT 'Demo Firma' TEMİZLİĞİ
    demo_tenants = session.exec(select(Base_Tenants).where(Base_Tenants.name == "Demo Firma")).all()
    
    for t in demo_tenants:
        product_count = session.exec(select(func.count(Base_Products.id)).where(Base_Products.tenant_id == t.id)).one()
        if product_count > 0:
            print(f"✅ Gerçek Demo Firma KORUNDU: {t.id} ({product_count} ürün)")
        else:
            print(f"🗑️ Sahte (Boş) Demo Firma SİLİNİYOR: {t.id}")
            # Hata almamak için önce firmaya bağlı sahte kullanıcı ve aboneliği sil
            for u in session.exec(select(Base_Users).where(Base_Users.tenant_id == t.id)).all():
                session.delete(u)
            for s in session.exec(select(Base_Subscriptions).where(Base_Subscriptions.tenant_id == t.id)).all():
                session.delete(s)
            # Firmayı sil
            session.delete(t)
            
    # 2. ABONELİK DURUMLARINI SIFIRLAMA
    all_subs = session.exec(select(Base_Subscriptions)).all()
    for sub in all_subs:
        sub.odemeDurumu = "Beklemede"
        session.add(sub)
        
    session.commit()
    print("🧹 Veri temizliği tamamlandı! Tüm abonelikler 'Beklemede' durumuna çekildi.")
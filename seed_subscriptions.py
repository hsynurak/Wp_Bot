from datetime import date, timedelta
from src.models.db_models import Base_Tenants, Base_Subscriptions
from src.database import engine
from sqlmodel import Session, select

with Session(engine) as session:
    # Tüm firmaları bul ve aboneliği olmayanlara oluştur
    tenants = session.exec(select(Base_Tenants)).all()
    plan_fiyatlari = {"Starter": 990, "Pro": 2490, "Enterprise": 5990}
    
    for tenant in tenants:
        existing = session.get(Base_Subscriptions, tenant.id)
        if not existing:
            sub = Base_Subscriptions(
                tenant_id=tenant.id,
                tutar=plan_fiyatlari.get(tenant.plan, 2490),
                odemeDurumu="Ödendi",
                sonOdeme=date.today() - timedelta(days=5),
                sonrakiOdeme=date.today() + timedelta(days=25)
            )
            session.add(sub)
    
    session.commit()
    print("Mevcut firmalar için abonelik kayıtları oluşturuldu!")
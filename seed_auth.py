from src.core.security import get_password_hash
from src.models.db_models import Base_Users, Base_Tenants, Base_Products, Base_Tenant_Customers, Base_Tenant_Staff, Base_Tenant_Settings
from src.database import engine
from sqlmodel import Session, select

with Session(engine) as session:
    # 1. Demo Tenant (Firma) oluştur
    tenant = Base_Tenants(name="Demo Firma")
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    
    # 2. Test Kullanıcısı oluştur
    user = Base_Users(
        email="admin@firma.com",
        hashed_password=get_password_hash("sifre123"),
        role="tenant",
        tenant_id=tenant.id,
    )
    session.add(user)
    session.commit()

    # 3. SAHİPSİZ VERİLERİ KURTAR VE FİRMAYA ZİMMETLE!
    # Ürünleri bağla
    for product in session.exec(select(Base_Products)).all():
        product.tenant_id = tenant.id
        session.add(product)
        
    # Müşterileri bağla
    for customer in session.exec(select(Base_Tenant_Customers)).all():
        customer.tenant_id = tenant.id
        session.add(customer)
        
    # Tezgahtarları bağla
    for staff in session.exec(select(Base_Tenant_Staff)).all():
        staff.tenant_id = tenant.id
        session.add(staff)
        
    # Ayarları bağla
    for setting in session.exec(select(Base_Tenant_Settings)).all():
        setting.tenant_id = tenant.id
        session.add(setting)
        
    session.commit()
    print("Demo firma kuruldu, admin@firma.com kullanıcısı açıldı ve tüm eski veriler firmaya zimmetlendi!")
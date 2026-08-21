from src.core.security import get_password_hash
from src.models.db_models import Base_Users
from src.database import engine
from sqlmodel import Session, select

with Session(engine) as session:
    # Var mı diye kontrol et
    existing = session.exec(select(Base_Users).where(Base_Users.email == "superadmin@humersoft.com")).first()
    if not existing:
        admin_user = Base_Users(
            email="superadmin@humersoft.com",
            hashed_password=get_password_hash("admin123"),
            role="superadmin",
            tenant_id=None # Superadmin bir tenant'a bağlı değildir
        )
        session.add(admin_user)
        session.commit()
        print("Superadmin hesabı başarıyla oluşturuldu! (superadmin@humersoft.com / admin123)")
    else:
        print("Superadmin hesabı zaten mevcut.")
import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from typing import Any, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, Enum, Index, String
from sqlmodel import Field, Relationship, SQLModel


class InventoryStatus(str, PyEnum):
    AKTIF = "AKTIF"
    PASIF = "PASIF"


class ActionType(str, PyEnum):
    SEPETE_GITTI = "SEPETE_GITTI"
    SATIN_ALINDI = "SATIN_ALINDI"
    BENZERI_ARANDI = "BENZERI_ARANDI"
    TEMSILCIYE_BAGLANDI = "TEMSILCIYE_BAGLANDI"


class Manufacturers(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class Base_Tenants(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    plan: str = Field(default="Pro")
    status: str = Field(default="Aktif")
    telefon: str = Field(default="")
    email: str = Field(default="")
    adres: str = Field(default="")
    yetkili: str = Field(default="")
    botNumara: str = Field(default="")
    wa_phone_number_id: Optional[str] = Field(default=None)
    wa_waba_id: Optional[str] = Field(default=None)
    wa_isletme_adi: Optional[str] = Field(default=None)
    wa_kalite_durumu: str = Field(default="GREEN")
    wa_baglanti_tarihi: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Base_Subscriptions(SQLModel, table=True):
    tenant_id: uuid.UUID = Field(primary_key=True, foreign_key="base_tenants.id")
    tutar: int
    odemeDurumu: str = Field(default="Beklemede")
    sonOdeme: Optional[date] = None
    sonrakiOdeme: Optional[date] = None
    gecikmeGun: int = Field(default=0)
    odemeYontemi: str = Field(default="Belirlenmedi")


class Base_Invoices(SQLModel, table=True):
    id: str = Field(primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="base_tenants.id")
    tutar: int
    tarih: date
    durum: str = Field(default="Ödenmedi")


class Base_Users(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True)
    hashed_password: str
    role: str = Field(default="tenant")
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="base_tenants.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Base_Products(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_code: str = Field(index=True, unique=True)
    manufacturer_id: uuid.UUID = Field(foreign_key="manufacturers.id")
    name: str = Field(default="Bilinmeyen Ürün")
    price: float = Field(default=0.0)
    category: str = Field(default="Belirtilmedi")
    status: str = Field(default="Aktif")
    stock: int = Field(default=0)
    image_url: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    season: Optional[str] = None
    embedding: Any = Field(default=None, sa_column=Column(Vector(512)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="base_tenants.id")


class Base_Tenant_Settings(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    firmaAdi: str = Field(default="")
    botTelefon: str = Field(default="")
    sepetLinki: str = Field(default="")
    katalogLinki: str = Field(default="")
    tezgahtarAktif: bool = Field(default=True)
    bot_settings: Any = Field(default_factory=dict, sa_column=Column(JSON))
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="base_tenants.id")


class Base_Tenant_Staff(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ad: str
    telefon: str = Field(default="")
    gorsel: str = Field(default="")
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="base_tenants.id")


class Base_Tenant_Customers(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    kod: str
    telefon: str = Field(unique=True)
    begeni: int = Field(default=0)
    begenmeme: int = Field(default=0)
    vektorEtiketleri: Any = Field(default_factory=list, sa_column=Column(JSON))
    begenilenUrunler: Any = Field(default_factory=list, sa_column=Column(JSON))
    begenilmeyenUrunler: Any = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="base_tenants.id")


class Base_Conversations(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="base_tenants.id")
    customer_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="base_tenant_customers.id",
    )
    wa_conversation_id: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime = Field(default_factory=datetime.utcnow)
    current_state: str = Field(default="idle")
    status: str = Field(default="active")


class Base_Messages(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(foreign_key="base_conversations.id")
    tenant_id: uuid.UUID = Field(foreign_key="base_tenants.id")
    wa_message_id: str = Field(unique=True, index=True)
    direction: str
    message_type: str
    content: Optional[str] = None
    media_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Base_Events(SQLModel, table=True):
    __table_args__ = (
        Index("idx_tenant_event_time", "tenant_id", "event_type", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="base_tenants.id")
    customer_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="base_tenant_customers.id",
    )
    conversation_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="base_conversations.id",
    )
    event_type: str
    product_id: Optional[uuid.UUID] = None
    metadata_json: Any = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Sellers(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    cart_url: Optional[str] = None
    catalog_url: Optional[str] = None
    is_online_only: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Customers(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phone: str = Field(unique=True, index=True)
    taste_vector: Any = Field(default=None, sa_column=Column(Vector(512)))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Customer_Interactions(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phone: str = Field(index=True)
    product_code: str
    interaction_type: str = Field(default="favorite")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Seller_Inventory(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    seller_id: uuid.UUID = Field(foreign_key="sellers.id")
    base_product_id: uuid.UUID = Field(foreign_key="base_products.id")
    seller_sku: str
    price: float
    status: InventoryStatus = Field(sa_column=Column(Enum(InventoryStatus)))


class Transactions(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    seller_id: uuid.UUID = Field(foreign_key="sellers.id")
    customer_id: uuid.UUID = Field(foreign_key="customers.id")
    inventory_id: uuid.UUID = Field(foreign_key="seller_inventory.id")
    action_type: ActionType = Field(sa_column=Column(Enum(ActionType)))
    quantity: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

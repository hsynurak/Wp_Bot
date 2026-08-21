import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Enum, String
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

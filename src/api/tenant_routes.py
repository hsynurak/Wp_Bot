"""Tenant (mağaza) paneli için ürün CRUD uç noktaları."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import Session, col, or_, select

from src.database import get_session
from src.models.db_models import (
    Base_Products,
    Base_Tenant_Customers,
    Base_Tenant_Settings,
    Base_Tenant_Staff,
)

router = APIRouter()


class ProductFrontendCreate(BaseModel):
    name: str
    image: str
    price: float
    category: str
    renk: str
    uretici: str
    bedenler: List[str]
    urunKodu: str
    sezon: str
    status: str
    stock: int = 0


class ProductFrontendResponse(BaseModel):
    id: uuid.UUID
    name: str
    image: str
    price: float
    category: str
    renk: str
    uretici: str
    bedenler: List[str]
    urunKodu: str
    sezon: str
    status: str
    stock: int


class PaginatedProductsResponse(BaseModel):
    items: list[ProductFrontendResponse]
    total: int
    page: int
    page_size: int


class TenantSettingsUpdate(BaseModel):
    firmaAdi: str = ""
    botTelefon: str = ""
    sepetLinki: str = ""
    katalogLinki: str = ""
    tezgahtarAktif: bool = True


class TenantSettingsResponse(BaseModel):
    id: uuid.UUID
    firmaAdi: str
    botTelefon: str
    sepetLinki: str
    katalogLinki: str
    tezgahtarAktif: bool


class StaffCreate(BaseModel):
    ad: str
    telefon: str = ""
    gorsel: str = ""


class StaffResponse(BaseModel):
    id: uuid.UUID
    ad: str
    telefon: str
    gorsel: str


class CustomerResponse(BaseModel):
    id: uuid.UUID
    kod: str
    telefon: str
    begeni: int
    begenmeme: int
    vektorEtiketleri: list = []
    begenilenUrunler: list = []
    begenilmeyenUrunler: list = []


class CustomerCreate(BaseModel):
    telefon: str
    begeni: int = 0
    begenmeme: int = 0
    vektorEtiketleri: list = []
    begenilenUrunler: list = []
    begenilmeyenUrunler: list = []


class CustomerPaginatedResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int


def _parse_manufacturer_id(uretici: str) -> uuid.UUID:
    try:
        return uuid.UUID(uretici)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="uretici alanı geçerli bir üretici UUID'si olmalıdır.",
        ) from exc


def _bedenler_to_size(bedenler: List[str]) -> str | None:
    cleaned = [beden.strip() for beden in bedenler if beden.strip()]
    if not cleaned:
        return None
    return ",".join(cleaned)


def _size_to_bedenler(size: str | None) -> List[str]:
    if not size:
        return []
    return [part.strip() for part in size.split(",") if part.strip()]


def _frontend_create_to_db(payload: ProductFrontendCreate) -> Base_Products:
    return Base_Products(
        model_code=payload.urunKodu,
        manufacturer_id=_parse_manufacturer_id(payload.uretici),
        name=payload.name,
        price=payload.price,
        category=payload.category,
        status=payload.status,
        stock=payload.stock,
        image_url=payload.image,
        color=payload.renk,
        size=_bedenler_to_size(payload.bedenler),
        season=payload.sezon,
        embedding=None,
    )


def _db_to_frontend_response(product: Base_Products) -> ProductFrontendResponse:
    return ProductFrontendResponse(
        id=product.id,
        name=product.name,
        image=product.image_url or "",
        price=product.price,
        category=product.category,
        renk=product.color or "",
        uretici=str(product.manufacturer_id),
        bedenler=_size_to_bedenler(product.size),
        urunKodu=product.model_code,
        sezon=product.season or "",
        status=product.status,
        stock=product.stock,
    )


def _build_search_filter(search: Optional[str]):
    if not search or not search.strip():
        return None
    term = f"%{search.strip()}%"
    return or_(
        col(Base_Products.name).ilike(term),
        col(Base_Products.model_code).ilike(term),
    )


def _get_or_create_tenant_settings(session: Session) -> Base_Tenant_Settings:
    settings = session.exec(select(Base_Tenant_Settings)).first()
    if settings is not None:
        return settings

    settings = Base_Tenant_Settings()
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def _to_tenant_settings_response(
    settings: Base_Tenant_Settings,
) -> TenantSettingsResponse:
    return TenantSettingsResponse(
        id=settings.id,
        firmaAdi=settings.firmaAdi,
        botTelefon=settings.botTelefon,
        sepetLinki=settings.sepetLinki,
        katalogLinki=settings.katalogLinki,
        tezgahtarAktif=settings.tezgahtarAktif,
    )


def _to_staff_response(staff: Base_Tenant_Staff) -> StaffResponse:
    return StaffResponse(
        id=staff.id,
        ad=staff.ad,
        telefon=staff.telefon,
        gorsel=staff.gorsel,
    )


def _to_customer_response(customer: Base_Tenant_Customers) -> CustomerResponse:
    return CustomerResponse(
        id=customer.id,
        kod=customer.kod,
        telefon=customer.telefon,
        begeni=customer.begeni,
        begenmeme=customer.begenmeme,
        vektorEtiketleri=customer.vektorEtiketleri or [],
        begenilenUrunler=customer.begenilenUrunler or [],
        begenilmeyenUrunler=customer.begenilmeyenUrunler or [],
    )


def _build_customer_search_filter(search: Optional[str]):
    if not search or not search.strip():
        return None
    term = f"%{search.strip()}%"
    return or_(
        col(Base_Tenant_Customers.kod).ilike(term),
        col(Base_Tenant_Customers.telefon).ilike(term),
    )


def _generate_customer_kod() -> str:
    return f"MŞT-{str(uuid.uuid4())[:4].upper()}"


def _get_customer_by_phone(
    session: Session,
    telefon: str,
) -> Base_Tenant_Customers | None:
    return session.exec(
        select(Base_Tenant_Customers).where(Base_Tenant_Customers.telefon == telefon)
    ).first()


@router.get("/products", response_model=PaginatedProductsResponse)
def list_products(
    session: Session = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
) -> PaginatedProductsResponse:
    search_filter = _build_search_filter(search)

    count_stmt = select(func.count(Base_Products.id))
    products_stmt = select(Base_Products)

    if search_filter is not None:
        count_stmt = count_stmt.where(search_filter)
        products_stmt = products_stmt.where(search_filter)

    products_stmt = products_stmt.order_by(Base_Products.created_at.desc())

    total: int = session.exec(count_stmt).one()
    offset = (page - 1) * page_size

    products = session.exec(
        products_stmt.offset(offset).limit(page_size)
    ).all()

    return PaginatedProductsResponse(
        items=[_db_to_frontend_response(product) for product in products],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/products", response_model=ProductFrontendResponse, status_code=201)
def create_product(
    payload: ProductFrontendCreate,
    session: Session = Depends(get_session),
) -> ProductFrontendResponse:
    existing = session.exec(
        select(Base_Products).where(Base_Products.model_code == payload.urunKodu)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Bu urunKodu zaten kayıtlı: {payload.urunKodu}",
        )

    product = _frontend_create_to_db(payload)
    session.add(product)
    session.commit()
    session.refresh(product)
    return _db_to_frontend_response(product)


@router.put("/products/{product_id}", response_model=ProductFrontendResponse)
def update_product(
    product_id: uuid.UUID,
    payload: ProductFrontendCreate,
    session: Session = Depends(get_session),
) -> ProductFrontendResponse:
    product = session.get(Base_Products, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    product.model_code = payload.urunKodu
    product.name = payload.name
    product.image_url = payload.image
    product.price = payload.price
    product.category = payload.category
    product.color = payload.renk
    product.season = payload.sezon
    product.status = payload.status
    product.stock = payload.stock
    product.manufacturer_id = _parse_manufacturer_id(payload.uretici)
    product.size = _bedenler_to_size(payload.bedenler)

    session.add(product)
    session.commit()
    session.refresh(product)
    return _db_to_frontend_response(product)


@router.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> None:
    product = session.get(Base_Products, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    session.delete(product)
    session.commit()


@router.get("/settings", response_model=TenantSettingsResponse)
def get_settings(session: Session = Depends(get_session)) -> TenantSettingsResponse:
    settings = _get_or_create_tenant_settings(session)
    return _to_tenant_settings_response(settings)


@router.put("/settings", response_model=TenantSettingsResponse)
def update_settings(
    payload: TenantSettingsUpdate,
    session: Session = Depends(get_session),
) -> TenantSettingsResponse:
    settings = _get_or_create_tenant_settings(session)

    settings.firmaAdi = payload.firmaAdi
    settings.botTelefon = payload.botTelefon
    settings.sepetLinki = payload.sepetLinki
    settings.katalogLinki = payload.katalogLinki
    settings.tezgahtarAktif = payload.tezgahtarAktif

    session.add(settings)
    session.commit()
    session.refresh(settings)
    return _to_tenant_settings_response(settings)


@router.get("/staff", response_model=list[StaffResponse])
def list_staff(session: Session = Depends(get_session)) -> list[StaffResponse]:
    staff_list = session.exec(select(Base_Tenant_Staff)).all()
    return [_to_staff_response(staff) for staff in staff_list]


@router.post("/staff", response_model=StaffResponse, status_code=201)
def create_staff(
    payload: StaffCreate,
    session: Session = Depends(get_session),
) -> StaffResponse:
    staff = Base_Tenant_Staff(
        ad=payload.ad,
        telefon=payload.telefon,
        gorsel=payload.gorsel,
    )
    session.add(staff)
    session.commit()
    session.refresh(staff)
    return _to_staff_response(staff)


@router.put("/staff/{staff_id}", response_model=StaffResponse)
def update_staff(
    staff_id: uuid.UUID,
    payload: StaffCreate,
    session: Session = Depends(get_session),
) -> StaffResponse:
    staff = session.get(Base_Tenant_Staff, staff_id)
    if staff is None:
        raise HTTPException(status_code=404, detail="Tezgahtar bulunamadı.")

    staff.ad = payload.ad
    staff.telefon = payload.telefon
    staff.gorsel = payload.gorsel

    session.add(staff)
    session.commit()
    session.refresh(staff)
    return _to_staff_response(staff)


@router.delete("/staff/{staff_id}", status_code=204)
def delete_staff(
    staff_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> None:
    staff = session.get(Base_Tenant_Staff, staff_id)
    if staff is None:
        raise HTTPException(status_code=404, detail="Tezgahtar bulunamadı.")

    session.delete(staff)
    session.commit()


@router.get("/customers", response_model=CustomerPaginatedResponse)
def list_customers(
    session: Session = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
) -> CustomerPaginatedResponse:
    search_filter = _build_customer_search_filter(search)

    count_stmt = select(func.count(Base_Tenant_Customers.id))
    customers_stmt = select(Base_Tenant_Customers)

    if search_filter is not None:
        count_stmt = count_stmt.where(search_filter)
        customers_stmt = customers_stmt.where(search_filter)

    customers_stmt = customers_stmt.order_by(Base_Tenant_Customers.created_at.desc())

    total: int = session.exec(count_stmt).one()
    offset = (page - 1) * page_size

    customers = session.exec(
        customers_stmt.offset(offset).limit(page_size)
    ).all()

    return CustomerPaginatedResponse(
        items=[_to_customer_response(customer) for customer in customers],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> CustomerResponse:
    customer = session.get(Base_Tenant_Customers, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")
    return _to_customer_response(customer)


@router.post("/customers", response_model=CustomerResponse, status_code=201)
def create_customer(
    payload: CustomerCreate,
    session: Session = Depends(get_session),
) -> CustomerResponse:
    if _get_customer_by_phone(session, payload.telefon) is not None:
        raise HTTPException(
            status_code=400,
            detail="Bu telefon numarası ile zaten bir müşteri kayıtlı.",
        )

    customer = Base_Tenant_Customers(
        kod=_generate_customer_kod(),
        telefon=payload.telefon,
        begeni=payload.begeni,
        begenmeme=payload.begenmeme,
        vektorEtiketleri=payload.vektorEtiketleri,
        begenilenUrunler=payload.begenilenUrunler,
        begenilmeyenUrunler=payload.begenilmeyenUrunler,
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return _to_customer_response(customer)


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerCreate,
    session: Session = Depends(get_session),
) -> CustomerResponse:
    customer = session.get(Base_Tenant_Customers, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

    existing = _get_customer_by_phone(session, payload.telefon)
    if existing is not None and existing.id != customer_id:
        raise HTTPException(
            status_code=400,
            detail="Bu telefon numarası ile zaten bir müşteri kayıtlı.",
        )

    customer.telefon = payload.telefon
    customer.begeni = payload.begeni
    customer.begenmeme = payload.begenmeme
    customer.vektorEtiketleri = payload.vektorEtiketleri
    customer.begenilenUrunler = payload.begenilenUrunler
    customer.begenilmeyenUrunler = payload.begenilmeyenUrunler

    session.add(customer)
    session.commit()
    session.refresh(customer)
    return _to_customer_response(customer)


@router.delete("/customers/{customer_id}", status_code=204)
def delete_customer(
    customer_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> None:
    customer = session.get(Base_Tenant_Customers, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

    session.delete(customer)
    session.commit()

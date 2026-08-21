"""Tenant (mağaza) paneli için ürün CRUD uç noktaları."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import Session, select

from src.database import get_session
from src.models.db_models import Base_Products

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


@router.get("/products", response_model=PaginatedProductsResponse)
def list_products(
    session: Session = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedProductsResponse:
    total: int = session.exec(select(func.count(Base_Products.id))).one()
    offset = (page - 1) * page_size

    products = session.exec(
        select(Base_Products)
        .offset(offset)
        .limit(page_size)
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

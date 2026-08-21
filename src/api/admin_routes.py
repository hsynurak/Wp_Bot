"""Super Admin firma yönetimi uç noktaları."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import Session, col, or_, select

from src.core.security import get_current_superadmin
from src.database import get_session
from src.models.db_models import Base_Tenants, Base_Users

router = APIRouter(prefix="/admin", tags=["Admin"])


class TenantCreate(BaseModel):
    name: str
    plan: str = "Pro"
    status: str = "Aktif"
    telefon: str = ""
    email: str = ""
    adres: str = ""
    yetkili: str = ""
    botNumara: str = ""


class TenantUpdate(BaseModel):
    name: str
    plan: str
    status: str
    telefon: str = ""
    email: str = ""
    adres: str = ""
    yetkili: str = ""
    botNumara: str = ""


class TenantStatusPatch(BaseModel):
    status: str = Field(description='Firma durumu: "Aktif" veya "Pasif"')


class TenantAdminResponse(BaseModel):
    id: uuid.UUID
    name: str
    plan: str
    status: str
    telefon: str
    email: str
    adres: str
    yetkili: str
    botNumara: str
    created_at: datetime
    urunToplam: int = 0
    musteriToplam: int = 0
    sepeteYonlendirme: int = 0
    temsilciyeBaglanti: int = 0
    benzeriArama: int = 0


class TenantPaginatedResponse(BaseModel):
    items: list[TenantAdminResponse]
    total: int
    page: int
    page_size: int


def _to_tenant_admin_response(tenant: Base_Tenants) -> TenantAdminResponse:
    return TenantAdminResponse(
        id=tenant.id,
        name=tenant.name,
        plan=tenant.plan,
        status=tenant.status,
        telefon=tenant.telefon,
        email=tenant.email,
        adres=tenant.adres,
        yetkili=tenant.yetkili,
        botNumara=tenant.botNumara,
        created_at=tenant.created_at,
    )


def _build_tenant_search_filter(search: Optional[str]):
    if not search or not search.strip():
        return None
    term = f"%{search.strip()}%"
    return or_(
        col(Base_Tenants.name).ilike(term),
        col(Base_Tenants.yetkili).ilike(term),
    )


def _get_tenant_or_404(session: Session, tenant_id: uuid.UUID) -> Base_Tenants:
    tenant = session.get(Base_Tenants, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Firma bulunamadı.")
    return tenant


@router.get("/tenants", response_model=TenantPaginatedResponse)
def list_tenants(
    session: Session = Depends(get_session),
    _: Base_Users = Depends(get_current_superadmin),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
) -> TenantPaginatedResponse:
    search_filter = _build_tenant_search_filter(search)

    count_stmt = select(func.count(Base_Tenants.id))
    tenants_stmt = select(Base_Tenants)

    if search_filter is not None:
        count_stmt = count_stmt.where(search_filter)
        tenants_stmt = tenants_stmt.where(search_filter)

    tenants_stmt = tenants_stmt.order_by(Base_Tenants.created_at.desc())

    total: int = session.exec(count_stmt).one()
    offset = (page - 1) * page_size

    tenants = session.exec(
        tenants_stmt.offset(offset).limit(page_size)
    ).all()

    return TenantPaginatedResponse(
        items=[_to_tenant_admin_response(tenant) for tenant in tenants],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/tenants", response_model=TenantAdminResponse, status_code=201)
def create_tenant(
    payload: TenantCreate,
    session: Session = Depends(get_session),
    _: Base_Users = Depends(get_current_superadmin),
) -> TenantAdminResponse:
    tenant = Base_Tenants(
        name=payload.name,
        plan=payload.plan,
        status=payload.status,
        telefon=payload.telefon,
        email=payload.email,
        adres=payload.adres,
        yetkili=payload.yetkili,
        botNumara=payload.botNumara,
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return _to_tenant_admin_response(tenant)


@router.get("/tenants/{tenant_id}", response_model=TenantAdminResponse)
def get_tenant(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session),
    _: Base_Users = Depends(get_current_superadmin),
) -> TenantAdminResponse:
    tenant = _get_tenant_or_404(session, tenant_id)
    return _to_tenant_admin_response(tenant)


@router.put("/tenants/{tenant_id}", response_model=TenantAdminResponse)
def update_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdate,
    session: Session = Depends(get_session),
    _: Base_Users = Depends(get_current_superadmin),
) -> TenantAdminResponse:
    tenant = _get_tenant_or_404(session, tenant_id)

    tenant.name = payload.name
    tenant.plan = payload.plan
    tenant.status = payload.status
    tenant.telefon = payload.telefon
    tenant.email = payload.email
    tenant.adres = payload.adres
    tenant.yetkili = payload.yetkili
    tenant.botNumara = payload.botNumara

    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return _to_tenant_admin_response(tenant)


@router.patch("/tenants/{tenant_id}/status", response_model=TenantAdminResponse)
def patch_tenant_status(
    tenant_id: uuid.UUID,
    payload: TenantStatusPatch,
    session: Session = Depends(get_session),
    _: Base_Users = Depends(get_current_superadmin),
) -> TenantAdminResponse:
    if payload.status not in {"Aktif", "Pasif"}:
        raise HTTPException(
            status_code=400,
            detail='Status alanı yalnızca "Aktif" veya "Pasif" olabilir.',
        )

    tenant = _get_tenant_or_404(session, tenant_id)
    tenant.status = payload.status

    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return _to_tenant_admin_response(tenant)

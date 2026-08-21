"""Super Admin firma yönetimi uç noktaları."""

from __future__ import annotations

import secrets
import string
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import Session, col, or_, select

from src.core.security import get_current_superadmin, get_password_hash
from src.database import get_session
from src.models.db_models import (
    Base_Invoices,
    Base_Subscriptions,
    Base_Tenant_Customers,
    Base_Tenants,
    Base_Users,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

PLAN_FIYATLARI = {"Starter": 990, "Pro": 2490, "Enterprise": 5990}


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
    urunAktif: int = 0
    urunPasif: int = 0
    musteriToplam: int = 0
    degerlendirmeSayisi: int = 0
    memnunSayisi: int = 0
    gorselGonderilen: int = 0
    gorselEslesen: int = 0
    sepeteYonlendirme: int = 0
    temsilciyeBaglanti: int = 0
    benzeriArama: int = 0


class TenantCreateResponse(TenantAdminResponse):
    gecici_sifre: str


class TenantPaginatedResponse(BaseModel):
    items: list[TenantAdminResponse]
    total: int
    page: int
    page_size: int


class AdminStatsResponse(BaseModel):
    firmaToplam: int
    firmaAktif: int
    musteriToplam: int
    gorselGonderilen: int = 0
    gorselEslesen: int = 0
    degerlendirmeSayisi: int = 0
    memnunSayisi: int = 0


class SubscriptionResponse(BaseModel):
    tenantId: uuid.UUID
    company: str
    email: str
    plan: str
    tutar: int
    odemeDurumu: str
    sonOdeme: date | None
    sonrakiOdeme: date | None
    gecikmeGun: int
    odemeYontemi: str


class SubscriptionStatusPatch(BaseModel):
    odemeDurumu: str


class InvoiceResponse(BaseModel):
    id: str
    tenantId: uuid.UUID
    company: str
    tutar: int
    tarih: date
    durum: str


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


def _to_subscription_response(
    subscription: Base_Subscriptions,
    tenant: Base_Tenants,
) -> SubscriptionResponse:
    return SubscriptionResponse(
        tenantId=subscription.tenant_id,
        company=tenant.name,
        email=tenant.email,
        plan=tenant.plan,
        tutar=subscription.tutar,
        odemeDurumu=subscription.odemeDurumu,
        sonOdeme=subscription.sonOdeme,
        sonrakiOdeme=subscription.sonrakiOdeme,
        gecikmeGun=subscription.gecikmeGun,
        odemeYontemi=subscription.odemeYontemi,
    )


def _to_invoice_response(
    invoice: Base_Invoices,
    tenant: Base_Tenants,
) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        tenantId=invoice.tenant_id,
        company=tenant.name,
        tutar=invoice.tutar,
        tarih=invoice.tarih,
        durum=invoice.durum,
    )


def _get_subscription_or_404(
    session: Session,
    tenant_id: uuid.UUID,
) -> Base_Subscriptions:
    subscription = session.get(Base_Subscriptions, tenant_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Abonelik bulunamadı.")
    return subscription


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


@router.post("/tenants", response_model=TenantCreateResponse, status_code=201)
def create_tenant(
    payload: TenantCreate,
    session: Session = Depends(get_session),
    _: Base_Users = Depends(get_current_superadmin),
) -> TenantCreateResponse:
    alphabet = string.ascii_letters + string.digits
    gecici_sifre = "".join(secrets.choice(alphabet) for _ in range(8))

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
    session.flush()

    user = Base_Users(
        email=payload.email,
        hashed_password=get_password_hash(gecici_sifre),
        role="tenant",
        tenant_id=tenant.id,
    )
    session.add(user)

    subscription = Base_Subscriptions(
        tenant_id=tenant.id,
        tutar=PLAN_FIYATLARI.get(payload.plan, 2490),
        sonrakiOdeme=date.today() + timedelta(days=30),
    )
    session.add(subscription)
    session.commit()
    session.refresh(tenant)

    return TenantCreateResponse(
        **_to_tenant_admin_response(tenant).model_dump(),
        gecici_sifre=gecici_sifre,
    )


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


@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(
    session: Session = Depends(get_session),
    _: Base_Users = Depends(get_current_superadmin),
) -> AdminStatsResponse:
    firma_toplam: int = session.exec(select(func.count(Base_Tenants.id))).one()
    firma_aktif: int = session.exec(
        select(func.count(Base_Tenants.id)).where(Base_Tenants.status == "Aktif")
    ).one()
    musteri_toplam: int = session.exec(
        select(func.count(Base_Tenant_Customers.id))
    ).one()

    return AdminStatsResponse(
        firmaToplam=firma_toplam,
        firmaAktif=firma_aktif,
        musteriToplam=musteri_toplam,
    )


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
def list_subscriptions(
    session: Session = Depends(get_session),
    _: Base_Users = Depends(get_current_superadmin),
) -> list[SubscriptionResponse]:
    subscriptions = session.exec(select(Base_Subscriptions)).all()
    results: list[SubscriptionResponse] = []

    for subscription in subscriptions:
        tenant = session.get(Base_Tenants, subscription.tenant_id)
        if tenant is None:
            continue
        results.append(_to_subscription_response(subscription, tenant))

    return results


@router.patch("/subscriptions/{tenant_id}", response_model=SubscriptionResponse)
def patch_subscription_status(
    tenant_id: uuid.UUID,
    payload: SubscriptionStatusPatch,
    session: Session = Depends(get_session),
    _: Base_Users = Depends(get_current_superadmin),
) -> SubscriptionResponse:
    subscription = _get_subscription_or_404(session, tenant_id)
    tenant = _get_tenant_or_404(session, tenant_id)

    subscription.odemeDurumu = payload.odemeDurumu

    session.add(subscription)
    session.commit()
    session.refresh(subscription)
    return _to_subscription_response(subscription, tenant)


@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices(
    session: Session = Depends(get_session),
    _: Base_Users = Depends(get_current_superadmin),
) -> list[InvoiceResponse]:
    invoices = session.exec(select(Base_Invoices)).all()
    results: list[InvoiceResponse] = []

    for invoice in invoices:
        tenant = session.get(Base_Tenants, invoice.tenant_id)
        if tenant is None:
            continue
        results.append(_to_invoice_response(invoice, tenant))

    return results

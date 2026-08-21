"""add subscriptions and invoices tables

Revision ID: f7a8b9c1d2e3
Revises: 67f94ca2f7b2
Create Date: 2026-08-21 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "f7a8b9c1d2e3"
down_revision: Union[str, None] = "67f94ca2f7b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "base_subscriptions",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("tutar", sa.Integer(), nullable=False),
        sa.Column("odemeDurumu", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("sonOdeme", sa.Date(), nullable=True),
        sa.Column("sonrakiOdeme", sa.Date(), nullable=True),
        sa.Column("gecikmeGun", sa.Integer(), nullable=False),
        sa.Column("odemeYontemi", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["base_tenants.id"]),
        sa.PrimaryKeyConstraint("tenant_id"),
    )
    op.create_table(
        "base_invoices",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("tutar", sa.Integer(), nullable=False),
        sa.Column("tarih", sa.Date(), nullable=False),
        sa.Column("durum", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["base_tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("base_invoices")
    op.drop_table("base_subscriptions")

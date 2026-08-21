"""add base_tenant_customers table

Revision ID: b2c3d4e5f6a7
Revises: 9af5c9bad4f7
Create Date: 2026-08-21 22:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "9af5c9bad4f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "base_tenant_customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kod", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("telefon", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("begeni", sa.Integer(), nullable=False),
        sa.Column("begenmeme", sa.Integer(), nullable=False),
        sa.Column("vektorEtiketleri", sa.JSON(), nullable=False),
        sa.Column("begenilenUrunler", sa.JSON(), nullable=False),
        sa.Column("begenilmeyenUrunler", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("base_tenant_customers")

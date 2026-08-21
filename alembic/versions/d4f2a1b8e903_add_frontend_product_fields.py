"""add frontend product fields to base_products

Revision ID: d4f2a1b8e903
Revises: c3e9c15caf30
Create Date: 2026-08-21 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "d4f2a1b8e903"
down_revision: Union[str, None] = "c3e9c15caf30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "base_products",
        sa.Column(
            "name",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="Bilinmeyen Ürün",
        ),
    )
    op.add_column(
        "base_products",
        sa.Column(
            "price",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "base_products",
        sa.Column(
            "category",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="Belirtilmedi",
        ),
    )
    op.add_column(
        "base_products",
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="Aktif",
        ),
    )
    op.add_column(
        "base_products",
        sa.Column(
            "stock",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("base_products", "stock")
    op.drop_column("base_products", "status")
    op.drop_column("base_products", "category")
    op.drop_column("base_products", "price")
    op.drop_column("base_products", "name")

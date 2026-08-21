"""add unique constraint to base_tenant_customers telefon

Revision ID: c3d4e5f6a7b8
Revises: 7801795f1d9d
Create Date: 2026-08-21 22:55:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "7801795f1d9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_base_tenant_customers_telefon",
        "base_tenant_customers",
        ["telefon"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_base_tenant_customers_telefon",
        "base_tenant_customers",
        type_="unique",
    )

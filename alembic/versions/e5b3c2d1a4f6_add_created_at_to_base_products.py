"""add created_at to base_products

Revision ID: e5b3c2d1a4f6
Revises: d4f2a1b8e903
Create Date: 2026-08-21 18:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5b3c2d1a4f6"
down_revision: Union[str, None] = "d4f2a1b8e903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "base_products",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_column("base_products", "created_at")

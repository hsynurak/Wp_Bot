"""add base_tenant_staff table

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-08-21 22:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "base_tenant_staff",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ad", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("telefon", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("gorsel", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("base_tenant_staff")

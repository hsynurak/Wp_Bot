"""add tenant admin fields to base_tenants

Revision ID: e6f7a8b9c0d1
Revises: bf7ccd79ca7b
Create Date: 2026-08-21 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "bf7ccd79ca7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "base_tenants",
        sa.Column(
            "plan",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="Pro",
        ),
    )
    op.add_column(
        "base_tenants",
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="Aktif",
        ),
    )
    op.add_column(
        "base_tenants",
        sa.Column(
            "telefon",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "base_tenants",
        sa.Column(
            "email",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "base_tenants",
        sa.Column(
            "adres",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "base_tenants",
        sa.Column(
            "yetkili",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "base_tenants",
        sa.Column(
            "botNumara",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("base_tenants", "botNumara")
    op.drop_column("base_tenants", "yetkili")
    op.drop_column("base_tenants", "adres")
    op.drop_column("base_tenants", "email")
    op.drop_column("base_tenants", "telefon")
    op.drop_column("base_tenants", "status")
    op.drop_column("base_tenants", "plan")

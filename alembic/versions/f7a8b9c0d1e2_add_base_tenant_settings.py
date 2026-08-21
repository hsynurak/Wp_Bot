"""add base_tenant_settings table

Revision ID: f7a8b9c0d1e2
Revises: 94bf5f2512c8
Create Date: 2026-08-21 22:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "94bf5f2512c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "base_tenant_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("firmaAdi", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("botTelefon", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("sepetLinki", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("katalogLinki", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tezgahtarAktif", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("base_tenant_settings")

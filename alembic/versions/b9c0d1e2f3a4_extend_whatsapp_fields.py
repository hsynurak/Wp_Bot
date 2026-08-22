"""extend whatsapp fields and nullable conversation relations

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-08-22 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "base_tenants",
        sa.Column("wa_isletme_adi", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "base_tenants",
        sa.Column(
            "wa_kalite_durumu",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="GREEN",
        ),
    )
    op.add_column(
        "base_tenants",
        sa.Column("wa_baglanti_tarihi", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "base_tenant_settings",
        sa.Column("bot_settings", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.alter_column(
        "base_conversations",
        "customer_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.alter_column(
        "base_events",
        "customer_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.alter_column(
        "base_events",
        "conversation_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "base_events",
        "conversation_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.alter_column(
        "base_events",
        "customer_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.alter_column(
        "base_conversations",
        "customer_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_column("base_tenant_settings", "bot_settings")
    op.drop_column("base_tenants", "wa_baglanti_tarihi")
    op.drop_column("base_tenants", "wa_kalite_durumu")
    op.drop_column("base_tenants", "wa_isletme_adi")

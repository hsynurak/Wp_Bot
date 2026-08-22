"""add whatsapp integration tables

Revision ID: a8b9c0d1e2f3
Revises: 55b6e721932b
Create Date: 2026-08-22 19:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "55b6e721932b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "base_tenants",
        sa.Column("wa_phone_number_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "base_tenants",
        sa.Column("wa_waba_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )

    op.create_table(
        "base_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("wa_conversation_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(), nullable=False),
        sa.Column("current_state", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["base_tenant_customers.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["base_tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "base_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("wa_message_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("direction", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("message_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("media_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["base_conversations.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["base_tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_base_messages_wa_message_id"),
        "base_messages",
        ["wa_message_id"],
        unique=True,
    )
    op.create_table(
        "base_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["base_conversations.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["base_tenant_customers.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["base_tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tenant_event_time",
        "base_events",
        ["tenant_id", "event_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_tenant_event_time", table_name="base_events")
    op.drop_table("base_events")
    op.drop_index(op.f("ix_base_messages_wa_message_id"), table_name="base_messages")
    op.drop_table("base_messages")
    op.drop_table("base_conversations")
    op.drop_column("base_tenants", "wa_waba_id")
    op.drop_column("base_tenants", "wa_phone_number_id")

"""add tenants users and tenant_id columns

Revision ID: d5e6f7a8b9c0
Revises: f4b9bc546137
Create Date: 2026-08-21 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "f4b9bc546137"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "base_tenants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "base_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["base_tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    for table in (
        "base_products",
        "base_tenant_settings",
        "base_tenant_staff",
        "base_tenant_customers",
    ):
        op.add_column(table, sa.Column("tenant_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "base_tenants",
            ["tenant_id"],
            ["id"],
        )


def downgrade() -> None:
    for table in (
        "base_tenant_customers",
        "base_tenant_staff",
        "base_tenant_settings",
        "base_products",
    ):
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")

    op.drop_table("base_users")
    op.drop_table("base_tenants")

"""Birden fazla head birleştirildi

Revision ID: 7801795f1d9d
Revises: b2c3d4e5f6a7, e31ac01a621f
Create Date: 2026-08-21 22:41:04.598531

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7801795f1d9d'
down_revision: Union[str, None] = ('b2c3d4e5f6a7', 'e31ac01a621f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

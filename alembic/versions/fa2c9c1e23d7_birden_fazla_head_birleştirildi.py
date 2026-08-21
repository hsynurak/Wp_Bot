"""Birden fazla head birleştirildi

Revision ID: fa2c9c1e23d7
Revises: c3d4e5f6a7b8, f8e7b48fdecc
Create Date: 2026-08-21 22:50:47.184260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa2c9c1e23d7'
down_revision: Union[str, None] = ('c3d4e5f6a7b8', 'f8e7b48fdecc')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

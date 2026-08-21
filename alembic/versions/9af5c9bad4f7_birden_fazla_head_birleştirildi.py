"""Birden fazla head birleştirildi

Revision ID: 9af5c9bad4f7
Revises: a1b2c3d4e5f6, edea55597120
Create Date: 2026-08-21 22:32:44.161509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9af5c9bad4f7'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'edea55597120')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

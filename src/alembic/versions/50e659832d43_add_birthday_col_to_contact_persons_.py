"""add birthday col to contact persons table

Revision ID: 50e659832d43
Revises: 
Create Date: 2026-01-02 17:33:25.928799

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50e659832d43'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('contact_persons', sa.Column('birthday', sa.String(), nullable = True))


def downgrade() -> None:
    """Downgrade schema."""
    pass

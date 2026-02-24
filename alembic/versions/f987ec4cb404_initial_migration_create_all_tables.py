"""Initial migration - create all tables

Revision ID: f987ec4cb404
Revises: 
Create Date: 2025-10-31 02:40:11.873687

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f987ec4cb404'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create all tables from current models."""
    from app.database import Base
    from app import models  # noqa: F401 — register all models with Base.metadata

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Downgrade schema: drop all tables (in reverse dependency order)."""
    from app.database import Base
    from app import models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

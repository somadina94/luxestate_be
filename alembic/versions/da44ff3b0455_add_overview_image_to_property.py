"""Add overview_image to Property

Revision ID: da44ff3b0455
Revises: 0adb6c56a735
Create Date: 2026-01-20 22:44:33.631957

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "da44ff3b0455"
down_revision: Union[str, Sequence[str], None] = "0adb6c56a735"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("properties")]
    if "overview_image" not in columns:
        op.add_column(
            "properties",
            sa.Column("overview_image", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("properties")]
    if "overview_image" in columns:
        op.drop_column("properties", "overview_image")

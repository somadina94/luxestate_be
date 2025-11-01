"""Create listing type

Revision ID: 360455739ad0
Revises: f987ec4cb404
Create Date: 2025-11-01 01:02:27.078311

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "360455739ad0"
down_revision: Union[str, Sequence[str], None] = "f987ec4cb404"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add listing_type column to properties table."""
    # Check if column already exists (idempotency - safe to run multiple times)
    conn = op.get_bind()
    inspector = inspect(conn)

    try:
        # Try to get columns from properties table
        columns = [col["name"] for col in inspector.get_columns("properties")]
    except Exception:
        # Table might not exist yet, skip migration (handled by create_all)
        columns = []

    if "listing_type" not in columns:
        # Add the column with a default value for existing rows
        # Use VARCHAR/String which works for both PostgreSQL and SQLite
        # Default to 'sale' for existing properties
        op.add_column(
            "properties",
            sa.Column(
                "listing_type", sa.String(20), nullable=False, server_default="sale"
            ),
        )


def downgrade() -> None:
    """Remove listing_type column from properties table."""
    # Check if column exists before dropping (idempotency)
    conn = op.get_bind()
    inspector = inspect(conn)

    try:
        columns = [col["name"] for col in inspector.get_columns("properties")]
        if "listing_type" in columns:
            op.drop_column("properties", "listing_type")
    except Exception:
        # Table might not exist, nothing to drop
        pass

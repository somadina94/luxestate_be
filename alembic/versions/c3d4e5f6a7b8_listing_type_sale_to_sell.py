"""Change listing_type value from sale to sell

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-03-06

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == "postgresql":
        # PostgreSQL: add 'sell' to enum if present, then update rows
        # Enum type name from SQLAlchemy create_all is often lowercase of the Python enum name
        op.execute(
            "ALTER TYPE listingtype ADD VALUE IF NOT EXISTS 'sell'"
        )
        op.execute(
            "UPDATE properties SET listing_type = 'sell' WHERE listing_type::text = 'sale'"
        )
    else:
        # SQLite and others: column stores string
        op.execute("UPDATE properties SET listing_type = 'sell' WHERE listing_type = 'sale'")


def downgrade() -> None:
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == "postgresql":
        op.execute(
            "UPDATE properties SET listing_type = 'sale' WHERE listing_type::text = 'sell'"
        )
        # Note: cannot remove enum value 'sell' from PostgreSQL enum easily; leave it
    else:
        op.execute("UPDATE properties SET listing_type = 'sale' WHERE listing_type = 'sell'")

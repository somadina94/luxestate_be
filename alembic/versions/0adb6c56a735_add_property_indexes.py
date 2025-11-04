"""Add performance indexes to properties table

Revision ID: 0adb6c56a735
Revises: 360455739ad0
Create Date: 2025-01-27 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "0adb6c56a735"
down_revision: Union[str, Sequence[str], None] = "360455739ad0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes to frequently queried columns in properties table."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # Get existing indexes
    try:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("properties")}
    except Exception:
        # Table might not exist yet
        existing_indexes = set()

    # Indexes for location-based queries
    if "ix_properties_city" not in existing_indexes:
        op.create_index("ix_properties_city", "properties", ["city"])

    if "ix_properties_state" not in existing_indexes:
        op.create_index("ix_properties_state", "properties", ["state"])

    if "ix_properties_country" not in existing_indexes:
        op.create_index("ix_properties_country", "properties", ["country"])

    # Index for price range queries
    if "ix_properties_price" not in existing_indexes:
        op.create_index("ix_properties_price", "properties", ["price"])

    # Composite index for common filter combinations (is_active + is_featured)
    if "ix_properties_active_featured" not in existing_indexes:
        op.create_index(
            "ix_properties_active_featured", "properties", ["is_active", "is_featured"]
        )

    # Index for agent queries
    if "ix_properties_agent_id" not in existing_indexes:
        op.create_index("ix_properties_agent_id", "properties", ["agent_id"])

    # Indexes for property type and status filtering
    if "ix_properties_property_type" not in existing_indexes:
        op.create_index("ix_properties_property_type", "properties", ["property_type"])

    if "ix_properties_status" not in existing_indexes:
        op.create_index("ix_properties_status", "properties", ["status"])

    if "ix_properties_listing_type" not in existing_indexes:
        op.create_index("ix_properties_listing_type", "properties", ["listing_type"])

    # Index for geospatial queries (latitude/longitude)
    if "ix_properties_location" not in existing_indexes:
        op.create_index(
            "ix_properties_location", "properties", ["latitude", "longitude"]
        )

    # Index for sorting by created_at
    if "ix_properties_created_at" not in existing_indexes:
        op.create_index("ix_properties_created_at", "properties", ["created_at"])


def downgrade() -> None:
    """Remove indexes from properties table."""
    indexes_to_drop = [
        "ix_properties_city",
        "ix_properties_state",
        "ix_properties_country",
        "ix_properties_price",
        "ix_properties_active_featured",
        "ix_properties_agent_id",
        "ix_properties_property_type",
        "ix_properties_status",
        "ix_properties_listing_type",
        "ix_properties_location",
        "ix_properties_created_at",
    ]

    conn = op.get_bind()
    inspector = inspect(conn)

    try:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("properties")}
    except Exception:
        existing_indexes = set()

    for index_name in indexes_to_drop:
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="properties")

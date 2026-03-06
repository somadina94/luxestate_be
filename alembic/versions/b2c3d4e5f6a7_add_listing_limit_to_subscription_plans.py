"""Add listing_limit to subscription_plans

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    columns = [c["name"] for c in insp.get_columns("subscription_plans")]
    if "listing_limit" not in columns:
        op.add_column(
            "subscription_plans",
            sa.Column("listing_limit", sa.Integer(), nullable=False, server_default="30"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    columns = [c["name"] for c in insp.get_columns("subscription_plans")]
    if "listing_limit" in columns:
        op.drop_column("subscription_plans", "listing_limit")

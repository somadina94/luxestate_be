"""Add overview_image, address, price, currency, year_built to favorites

Revision ID: a1b2c3d4e5f6
Revises: da44ff3b0455
Create Date: 2026-02-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "da44ff3b0455"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "favorites",
        sa.Column("overview_image", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "favorites",
        sa.Column("address", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "favorites",
        sa.Column("price", sa.Float(), nullable=True),
    )
    op.add_column(
        "favorites",
        sa.Column("currency", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "favorites",
        sa.Column("year_built", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("favorites", "year_built")
    op.drop_column("favorites", "currency")
    op.drop_column("favorites", "price")
    op.drop_column("favorites", "address")
    op.drop_column("favorites", "overview_image")

"""Add overview_image to Property

Revision ID: da44ff3b0455
Revises: 0adb6c56a735
Create Date: 2026-01-20 22:44:33.631957

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "da44ff3b0455"
down_revision: Union[str, Sequence[str], None] = "0adb6c56a735"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "properties", sa.Column("overview_image", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("properties", "overview_image")

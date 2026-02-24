"""Add user/agent names and property_title to conversations

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("user_first_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("user_last_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("agent_first_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("agent_last_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("property_title", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "property_title")
    op.drop_column("conversations", "agent_last_name")
    op.drop_column("conversations", "agent_first_name")
    op.drop_column("conversations", "user_last_name")
    op.drop_column("conversations", "user_first_name")

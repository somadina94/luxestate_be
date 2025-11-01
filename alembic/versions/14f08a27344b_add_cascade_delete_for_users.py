"""Add cascade delete for users

Revision ID: 14f08a27344b
Revises: 360455739ad0
Create Date: 2025-11-01 02:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "14f08a27344b"
down_revision: Union[str, Sequence[str], None] = "360455739ad0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add CASCADE delete constraints to all foreign keys referencing users.id."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # Dictionary mapping table names to their foreign key columns that reference users.id
    # Format: table_name -> [(column_name, nullable)]
    fk_updates = {
        "properties": [("agent_id", False)],
        "notifications": [("user_id", True)],
        "user_push_tokens": [("user_id", True)],
        "tickets": [("user_id", True)],
        "ticket_messages": [("sender_id", True)],
        "conversations": [("user_id", True), ("agent_id", True), ("admin_id", True)],
        "messages": [("sender_id", True)],
        "subscriptions": [("user_id", True)],
        "audit_logs": [("user_id", True)],
    }

    # Favorite table already has CASCADE, skip it

    # For PostgreSQL and other databases that support DROP/ADD CONSTRAINT
    if conn.dialect.name in ("postgresql", "mysql", "mssql"):
        for table_name, columns in fk_updates.items():
            try:
                # Check if table exists
                if table_name not in inspector.get_table_names():
                    continue

                # Get existing foreign keys
                fks = inspector.get_foreign_keys(table_name)

                for column_name, nullable in columns:
                    # Find the foreign key constraint
                    fk = next(
                        (
                            fk
                            for fk in fks
                            if fk["constrained_columns"] == [column_name]
                            and fk["referred_table"] == "users"
                        ),
                        None,
                    )

                    if fk:
                        fk_name = fk["name"]
                        # Drop the old foreign key
                        op.drop_constraint(fk_name, table_name, type_="foreignkey")

                        # Recreate with CASCADE
                        op.create_foreign_key(
                            fk_name if fk_name else f"fk_{table_name}_{column_name}",
                            table_name,
                            "users",
                            [column_name],
                            ["id"],
                            ondelete="CASCADE",
                        )
            except Exception as e:
                # Log error but continue with other tables
                print(f"Warning: Could not update {table_name}.{column_name}: {e}")

    # For SQLite, we need to recreate the table (SQLite doesn't support DROP CONSTRAINT)
    elif conn.dialect.name == "sqlite":
        # SQLite doesn't support altering foreign keys easily
        # In practice, this migration would be handled during table creation
        # For existing SQLite databases, you'd need to recreate tables
        print(
            "Note: SQLite doesn't support altering foreign keys. "
            "Tables will need to be recreated with CASCADE constraints."
        )


def downgrade() -> None:
    """Remove CASCADE delete constraints (revert to no action)."""
    conn = op.get_bind()
    inspector = inspect(conn)

    fk_updates = {
        "properties": [("agent_id", False)],
        "notifications": [("user_id", True)],
        "user_push_tokens": [("user_id", True)],
        "tickets": [("user_id", True)],
        "ticket_messages": [("sender_id", True)],
        "conversations": [("user_id", True), ("agent_id", True), ("admin_id", True)],
        "messages": [("sender_id", True)],
        "subscriptions": [("user_id", True)],
        "audit_logs": [("user_id", True)],
    }

    if conn.dialect.name in ("postgresql", "mysql", "mssql"):
        for table_name, columns in fk_updates.items():
            try:
                if table_name not in inspector.get_table_names():
                    continue

                fks = inspector.get_foreign_keys(table_name)

                for column_name, nullable in columns:
                    fk = next(
                        (
                            fk
                            for fk in fks
                            if fk["constrained_columns"] == [column_name]
                            and fk["referred_table"] == "users"
                        ),
                        None,
                    )

                    if fk:
                        fk_name = fk["name"]
                        op.drop_constraint(fk_name, table_name, type_="foreignkey")
                        # Recreate without CASCADE (default behavior)
                        op.create_foreign_key(
                            fk_name if fk_name else f"fk_{table_name}_{column_name}",
                            table_name,
                            "users",
                            [column_name],
                            ["id"],
                        )
            except Exception as e:
                print(f"Warning: Could not revert {table_name}.{column_name}: {e}")

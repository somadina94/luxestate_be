import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from app.database import Base
from app import models
from app.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url from environment variable or settings
# This allows us to use DATABASE_URL from .env file instead of alembic.ini
database_url = os.getenv("DATABASE_URL") or getattr(settings, "DATABASE_URL", None)

# Always override if we have a DATABASE_URL (not just the default SQLite)
# This ensures PostgreSQL URLs work correctly in deploy.sh
if database_url:
    # Remove any surrounding quotes that might be in the env var
    database_url = database_url.strip().strip('"').strip("'")
    # Only skip if it's the exact default SQLite path from alembic.ini
    if database_url != "sqlite:///./luxestate.db":
        config.set_main_option("sqlalchemy.url", database_url)
else:
    # Log warning if no DATABASE_URL found (for debugging on EC2)
    import sys
    print("WARNING: No DATABASE_URL found in environment or settings. Using default from alembic.ini", file=sys.stderr)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

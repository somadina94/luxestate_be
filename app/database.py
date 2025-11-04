from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
import os

# Safety check: Prevent accidental production database usage in tests
if os.getenv("TESTING") == "true" and not settings.DATABASE_URL.startswith("sqlite"):
    import warnings
    warnings.warn(
        f"⚠️  WARNING: Tests are configured but DATABASE_URL points to non-SQLite: {settings.DATABASE_URL[:50]}...\n"
        "This could cause tests to write to production database!\n"
        "Set DATABASE_URL=sqlite:///:memory: before importing app modules.",
        RuntimeWarning,
        stacklevel=2
    )

# SQLite needs check_same_thread, PostgreSQL doesn't
if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy.pool import NullPool
    connect_args = {"check_same_thread": False}
    # SQLite doesn't benefit from connection pooling and has limited pool options
    # SQLite doesn't support max_overflow, pool_timeout, pool_recycle, or pool_pre_ping
    # Use NullPool (no pooling) for SQLite
    engine_kwargs = {
        "connect_args": connect_args,
        "poolclass": NullPool,  # No connection pooling for SQLite
        "echo": False,
    }
else:
    # PostgreSQL connection args with timeout settings
    # Important: Use connection pooling URL (port 6543) for Supabase on EC2
    # Direct connection (port 5432) can cause connection limits and timeout issues
    # Supabase has a limit of direct connections (typically 60), but pooling allows many more
    connect_args = {
        "connect_timeout": 10,  # 10 second connection timeout
    }
    # PostgreSQL connection pooling - important for performance
    engine_kwargs = {
        "connect_args": connect_args,
        "pool_size": 20,  # Number of connections to maintain
        "max_overflow": 10,  # Additional connections when pool is exhausted
        "pool_pre_ping": True,  # Verify connections before using
        "pool_recycle": 3600,  # Recycle connections after 1 hour
        "pool_timeout": 30,  # Wait up to 30 seconds for connection from pool
        "echo": False,  # Set to True for SQL query logging (debug only)
    }

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

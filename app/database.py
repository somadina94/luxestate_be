from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# SQLite needs check_same_thread, PostgreSQL doesn't
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # SQLite doesn't benefit much from connection pooling
    engine_kwargs = {
        "connect_args": connect_args,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": False,
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

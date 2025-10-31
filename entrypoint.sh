#!/bin/bash
set -e

# Wait for database to be ready (if using external database)
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database to be ready..."
    max_attempts=60
    attempt=0
    until python -c "
import sys
try:
    from sqlalchemy import create_engine, text
    engine = create_engine('$DATABASE_URL')
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "Database connection failed after $max_attempts attempts"
            exit 1
        fi
        echo "Database is unavailable - sleeping (attempt $attempt/$max_attempts)"
        sleep 2
    done
    echo "Database is ready!"
fi

# Run database migrations (optional, controlled by env var)
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head || echo "Migration failed, continuing anyway..."
fi

# Execute the main command
exec "$@"


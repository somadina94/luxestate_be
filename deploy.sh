#!/bin/bash

# Simple deployment script for EC2 (no Docker, no AWS CLI)
# Usage: ./deploy.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration (use the invoking user if run with sudo)
RUN_USER=${SUDO_USER:-$USER}
APP_DIR=${APP_DIR:-/home/$RUN_USER/luxestate}
PYTHON=${PYTHON:-python3}
PORT=${PORT:-3002}
SERVICE_NAME=${SERVICE_NAME:-luxestate}

echo -e "${GREEN}Starting deployment...${NC}"

echo -e "${YELLOW}Preparing app directory: ${APP_DIR}${NC}"
mkdir -p "${APP_DIR}"
cd "${APP_DIR}"

if [ -d .git ]; then
  echo -e "${YELLOW}Fetching latest code...${NC}"
  git fetch --all --prune
  # Detect default branch from origin
  DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "")
  if [ -z "$DEFAULT_BRANCH" ]; then
    # Try to detect from available branches
    DEFAULT_BRANCH=$(git branch -r | grep -E 'origin/(main|master)' | head -1 | sed 's@origin/@@' | xargs)
  fi
  if [ -n "$DEFAULT_BRANCH" ]; then
    echo -e "${GREEN}Resetting to origin/${DEFAULT_BRANCH}...${NC}"
    git reset --hard "origin/${DEFAULT_BRANCH}"
  else
    echo -e "${YELLOW}Could not detect default branch, resetting to origin/HEAD...${NC}"
    git reset --hard origin/HEAD 2>/dev/null || git reset --hard HEAD
  fi
else
  echo -e "${YELLOW}Cloning repository...${NC}"
  git clone "https://github.com/somadina94/luxestate_be.git" .
fi

echo -e "${YELLOW}Creating/updating Python virtual environment...${NC}"
if [ ! -d venv ]; then
  ${PYTHON} -m venv venv
fi
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  echo -e "${RED}.env file not found at ${APP_DIR}. Create it before running the service.${NC}"
  exit 1
fi

# Ensure SQLite database directory exists and is writable (if using SQLite)
DB_PATH=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2- | sed "s/^[\"']//;s/[\"']$//" || echo "sqlite:////home/${RUN_USER}/luxestate/luxestate.db")
if echo "$DB_PATH" | grep -q "^sqlite"; then
  # Extract absolute path from sqlite:////path/to/db.db
  SQLITE_FILE=$(echo "$DB_PATH" | sed 's|sqlite:///||')
  SQLITE_DIR=$(dirname "$SQLITE_FILE")
  echo -e "${YELLOW}Ensuring SQLite database directory is writable: ${SQLITE_DIR}${NC}"
  mkdir -p "$SQLITE_DIR"
  touch "$SQLITE_FILE" 2>/dev/null || true
  chmod 664 "$SQLITE_FILE" 2>/dev/null || true
  chown ${RUN_USER}:${RUN_USER} "$SQLITE_DIR" "$SQLITE_FILE" 2>/dev/null || true
fi

# Load .env (requires KEY=VALUE with proper quoting)
echo -e "${YELLOW}Loading environment variables from ${APP_DIR}/.env...${NC}"
set -a
. "${APP_DIR}/.env"
set +a

# Verify critical env is loaded
if [ -z "${DATABASE_URL:-}" ]; then
  echo -e "${RED}DATABASE_URL is not set after loading .env. Aborting migrations.${NC}"
  exit 1
fi
echo -e "${GREEN}DATABASE_URL loaded.${NC}"

# Run migrations (skip for SQLite since tables are auto-created)
if echo "${DATABASE_URL:-}" | grep -q "^sqlite"; then
  echo -e "${YELLOW}Skipping migrations for SQLite (tables auto-created on startup)${NC}"
else
  echo -e "${YELLOW}Running database migrations...${NC}"
  # Export DATABASE_URL explicitly to ensure alembic can access it
  export DATABASE_URL
  # Debug: Show DATABASE_URL (without password for security)
  DB_URL_FOR_LOG=$(echo "$DATABASE_URL" | sed 's/:[^:@]*@/:***@/')
  echo -e "${YELLOW}Using DATABASE_URL: ${DB_URL_FOR_LOG}${NC}"
  
  # Test database connection before running migrations
  echo -e "${YELLOW}Testing database connection...${NC}"
  # Get EC2 public IP for Supabase whitelist reference
  EC2_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s https://api.ipify.org 2>/dev/null || echo "unknown")
  if [ "$EC2_IP" != "unknown" ]; then
    echo -e "${YELLOW}Your EC2 Public IP: ${EC2_IP}${NC}"
    echo -e "${YELLOW}Add this IP to Supabase whitelist: ${EC2_IP}/32${NC}"
  fi
  cd "${APP_DIR}"
  source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
  if python -c "
import sys
try:
    from sqlalchemy import create_engine, text
    # Try with IPv4 only (disable IPv6) if connection fails
    import socket
    # Force IPv4 by using socket options
    connect_args = {'connect_timeout': 10}
    # If DATABASE_URL contains IPv6, try forcing IPv4
    db_url = '$DATABASE_URL'
    # Try connection
    engine = create_engine(db_url, connect_args=connect_args)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('Database connection successful')
    sys.exit(0)
except Exception as e:
    # If IPv6 fails, try to suggest IPv4 solution or connection pooling
    error_msg = str(e)
    if 'Network is unreachable' in error_msg or 'IPv6' in error_msg:
        print(f'Connection failed (possibly IPv6 issue): {e}', file=sys.stderr)
        print('TIP: Try using Supabase Connection Pooling URL (port 6543) instead of direct connection (port 5432)', file=sys.stderr)
        print('Example: postgresql://user:pass@db.xxx.supabase.co:6543/postgres', file=sys.stderr)
    else:
        print(f'Database connection failed: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1; then
    echo -e "${GREEN}Database connection successful! Proceeding with migrations...${NC}"
  else
    echo -e "${RED}Database connection failed! Cannot run migrations.${NC}"
    echo -e "${YELLOW}Issue detected: IPv6 connectivity problem${NC}"
    echo -e "${YELLOW}Solution: Use Supabase Connection Pooling URL (port 6543) instead of direct connection${NC}"
    echo -e ""
    echo -e "${YELLOW}Steps to fix:${NC}"
    echo -e "  1. Go to Supabase Dashboard → Settings → Database → Connection Pooling"
    echo -e "  2. Copy the 'Connection string' (Session mode) - it uses port 6543"
    echo -e "  3. Update DATABASE_URL in your .env file to use port 6543 instead of 5432"
    echo -e "     Example: postgresql://postgres:***@db.xxx.supabase.co:6543/postgres"
    echo -e "  4. Re-run deployment"
    echo -e ""
    echo -e "${YELLOW}Alternative: Force IPv4 by modifying your .env DATABASE_URL${NC}"
    echo -e "${YELLOW}Continuing deployment without migrations. You can run migrations manually later.${NC}"
    # Don't exit - allow deployment to continue, migrations can be run later
  fi
  
  # Run migrations if connection test passed or we're continuing anyway
  # First, check what migrations are available
  echo -e "${YELLOW}Checking available migrations...${NC}"
  if command -v alembic >/dev/null 2>&1; then
    ALEMBIC_CMD=alembic
  else
    ALEMBIC_CMD="${APP_DIR}/venv/bin/alembic"
  fi
  
  # Verify migration files exist
  if [ ! -f "${APP_DIR}/alembic/versions/360455739ad0_create_listing_type.py" ]; then
    echo -e "${RED}ERROR: Migration file 360455739ad0_create_listing_type.py not found!${NC}"
    echo -e "${YELLOW}Make sure all migration files are committed and deployed.${NC}"
    ls -la "${APP_DIR}/alembic/versions/" 2>&1 || echo "Could not list migration files"
  fi
  
  # Show available migrations
  echo -e "${YELLOW}Available migrations:${NC}"
  $ALEMBIC_CMD history 2>&1 | head -10 || echo "Could not list migration history"
  
  # Check current revision
  CURRENT_REV=$($ALEMBIC_CMD current 2>/dev/null | grep -oE '[a-f0-9]{12}' | head -1 || echo "")
  echo -e "${YELLOW}Current database revision: ${CURRENT_REV:-none}${NC}"
  
  # If database is trying to reference 360455739ad0 but can't find it, reset
  # This happens when database thinks it's already at 360455739ad0 but the file doesn't exist
  if [ -n "$CURRENT_REV" ] && [ "$CURRENT_REV" = "360455739ad0" ]; then
    # Check if the migration file actually exists
    if [ ! -f "${APP_DIR}/alembic/versions/360455739ad0_create_listing_type.py" ]; then
      echo -e "${YELLOW}Database is at 360455739ad0 but migration file missing. Resetting...${NC}"
      $ALEMBIC_CMD stamp f987ec4cb404 2>&1 || echo "Could not reset revision"
    fi
  fi
  
  # If database is at a revision that doesn't exist, reset it
  if [ -n "$CURRENT_REV" ] && [ "$CURRENT_REV" != "f987ec4cb404" ] && [ "$CURRENT_REV" != "360455739ad0" ]; then
    echo -e "${YELLOW}Database is at unknown revision ${CURRENT_REV}, resetting to base revision...${NC}"
    $ALEMBIC_CMD stamp f987ec4cb404 2>&1 || echo "Could not stamp base revision"
  fi
  
  # If no revision, stamp the base
  if [ -z "$CURRENT_REV" ]; then
    echo -e "${YELLOW}No revision found, stamping base revision...${NC}"
    $ALEMBIC_CMD stamp f987ec4cb404 2>&1 || echo "Could not stamp base revision"
  fi
  
  # Run migrations
  echo -e "${YELLOW}Running migrations...${NC}"
  $ALEMBIC_CMD upgrade head || {
    echo -e "${RED}Migration failed. See alembic logs above.${NC}"
    echo -e "${YELLOW}Debug info:${NC}"
    echo -e "  Current revision: $($ALEMBIC_CMD current 2>&1 || echo 'unknown')"
    echo -e "  Migration files present:"
    ls -la "${APP_DIR}/alembic/versions/"*.py 2>&1 || echo "  Could not list files"
    echo -e "  Try manually: alembic stamp f987ec4cb404 && alembic upgrade head${NC}"
    # Don't exit - allow deployment to continue
  }
fi

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
if [ $(id -u) -ne 0 ]; then
  SUDO=sudo
else
  SUDO=
fi

echo -e "${YELLOW}Writing systemd service: ${SERVICE_FILE}${NC}"
# Extract DATABASE_URL from .env for explicit setting (systemd EnvironmentFile can be unreliable with quotes)
DATABASE_URL_VALUE=""
if [ -f "${APP_DIR}/.env" ]; then
  DATABASE_URL_VALUE=$(grep "^DATABASE_URL=" "${APP_DIR}/.env" | cut -d'=' -f2- | sed "s/^[\"']//;s/[\"']$//")
fi

# Build service file content
SERVICE_CONTENT="[Unit]
Description=LuxeState API (FastAPI Uvicorn)
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env"

# Add explicit DATABASE_URL if we found it
if [ -n "$DATABASE_URL_VALUE" ]; then
  SERVICE_CONTENT="${SERVICE_CONTENT}
Environment=DATABASE_URL=${DATABASE_URL_VALUE}"
fi

SERVICE_CONTENT="${SERVICE_CONTENT}
ExecStart=${APP_DIR}/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target"

${SUDO} bash -c "cat > ${SERVICE_FILE}" <<ENDOFFILE
${SERVICE_CONTENT}
ENDOFFILE

echo -e "${YELLOW}Reloading systemd and restarting service...${NC}"
${SUDO} systemctl daemon-reload
${SUDO} systemctl enable ${SERVICE_NAME}
${SUDO} systemctl restart ${SERVICE_NAME}

echo -e "${YELLOW}Waiting for app to be ready...${NC}"
sleep 3
if curl -fsS http://localhost:${PORT}/healthy >/dev/null 2>&1; then
  echo -e "${GREEN}App is healthy on port ${PORT}!${NC}"
else
  echo -e "${YELLOW}Health endpoint not responding yet. Check logs: ${SUDO} journalctl -u ${SERVICE_NAME} -f${NC}"
fi

echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}Follow logs: ${SUDO} journalctl -u ${SERVICE_NAME} -f${NC}"


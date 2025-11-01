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
  # Run alembic from the virtual environment with DATABASE_URL explicitly set
  alembic upgrade head || {
    echo -e "${RED}Migration failed. See alembic logs above.${NC}"
    exit 1
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


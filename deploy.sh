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

echo -e "${YELLOW}Running database migrations...${NC}"
alembic upgrade head || {
  echo -e "${RED}Migration failed. See alembic logs above.${NC}"
  exit 1
}

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
if [ $(id -u) -ne 0 ]; then
  SUDO=sudo
else
  SUDO=
fi

echo -e "${YELLOW}Writing systemd service: ${SERVICE_FILE}${NC}"
${SUDO} bash -c "cat > ${SERVICE_FILE}" <<EOF
[Unit]
Description=LuxeState API (FastAPI Uvicorn)
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

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


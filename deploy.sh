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
  # Removed aggressive clean to avoid deleting untracked files like .env
else
  echo -e "${YELLOW}Cloning repository...${NC}"
  # Replace with your repo URL if needed
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

# Load .env file for migrations (Python-based parser to handle special chars)
echo -e "${YELLOW}Loading environment variables from ${APP_DIR}/.env...${NC}"
ENV_FILE="${APP_DIR}/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo -e "${RED}.env file not found at $ENV_FILE${NC}"
  exit 1
fi

# Use Python to parse and write a temporary exports file, then source it
TEMP_EXPORTS="/tmp/luxestate_exports_$$.sh"
python3 <<PYTHON_SCRIPT || {
  echo -e "${RED}Failed parsing .env. Please check formatting.${NC}";
  exit 1;
}
import os
import re
import sys

env_file = os.environ.get('ENV_FILE')
if not env_file or not os.path.isfile(env_file):
    sys.stderr.write(f".env not found at {env_file}\n")
    sys.exit(1)

def parse_lines(filename):
    with open(filename, 'r') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)[:=]\s*(.+)$', line)
            if not m and '=' in line and not line.startswith('='):
                key, value = line.split('=', 1)
            elif m:
                key, value = m.groups()
            else:
                continue
            # Trim surrounding quotes but preserve interior
            value = value.strip().strip('"').strip("'")
            # Escape single quotes for safe shell export
            value = value.replace("'", "'\\''")
            yield key, value

out = os.environ.get('TEMP_EXPORTS')
with open(out, 'w') as fh:
    for k, v in parse_lines(env_file):
        fh.write(f"export {k}='{v}'\n")
PYTHON_SCRIPT

# Source the generated exports and remove the temp file
set -a
. "$TEMP_EXPORTS"
set +a
rm -f "$TEMP_EXPORTS"

# Verify critical env is loaded
if [ -z "${DATABASE_URL:-}" ]; then
  echo -e "${RED}DATABASE_URL is not set after loading .env.${NC}"
  echo -e "${YELLOW}Trying to load from .env directly...${NC}"
  # Fallback: direct source attempt (might fail if .env has special chars)
  [ -f .env ] && source <(grep -v '^#' .env | grep '=' | sed "s/:/=/g")
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo -e "${RED}DATABASE_URL still not set. Please check your .env file.${NC}"
  exit 1
fi

echo -e "${GREEN}DATABASE_URL loaded successfully${NC}"

echo -e "${YELLOW}Running database migrations...${NC}"
# Ensure DATABASE_URL is available to alembic
export DATABASE_URL
alembic upgrade head || {
  echo -e "${RED}Migration failed. Error details:${NC}"
  alembic upgrade head 2>&1 | head -20
  echo -e "${YELLOW}Continuing despite migration failure...${NC}"
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


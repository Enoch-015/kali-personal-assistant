#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[install_redis] %s\n' "$*"
}

log "Updating package index and installing prerequisites"
sudo apt-get update
sudo apt-get install -y lsb-release curl gpg >/dev/null

KEYRING="/usr/share/keyrings/redis-archive-keyring.gpg"
REPO_FILE="/etc/apt/sources.list.d/redis.list"

if [[ ! -f "${KEYRING}" ]]; then
  log "Importing Redis signing key"
  curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o "${KEYRING}"
  sudo chmod 644 "${KEYRING}"
else
  log "Redis signing key already present — skipping import"
fi

if [[ ! -f "${REPO_FILE}" ]]; then
  log "Adding Redis APT repository"
  echo "deb [signed-by=${KEYRING}] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee "${REPO_FILE}" >/dev/null
else
  log "Redis repository already configured"
fi

log "Installing Redis server"
sudo apt-get update >/dev/null
sudo apt-get install -y redis >/dev/null

restart_with_service() {
  if command -v service >/dev/null; then
    log "Restarting redis-server via service command"
    if ! sudo service redis-server restart >/dev/null 2>&1; then
      sudo service redis-server start >/dev/null 2>&1 || true
    fi
  else
    log "'service' command not available; please start redis-server manually" >&2
  fi
}

log "Enabling and starting Redis service"
if command -v systemctl >/dev/null; then
  if systemctl list-unit-files >/dev/null 2>&1; then
    sudo systemctl enable redis-server >/dev/null
    sudo systemctl restart redis-server >/dev/null
  else
    log "systemd not active; falling back to service command"
    restart_with_service
  fi
else
  restart_with_service
fi

if command -v update-rc.d >/dev/null 2>&1; then
  sudo update-rc.d redis-server defaults >/dev/null 2>&1 || true
fi

log "Redis installation and startup complete."

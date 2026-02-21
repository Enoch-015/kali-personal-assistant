#!/usr/bin/env bash
#
# Start Vault in Dev Mode (Local Development)
#
# This script starts HashiCorp Vault locally in dev mode for development.
# It's simpler and faster than using Docker for day-to-day development.
#
# Prerequisites:
#   - Vault CLI installed (brew install vault / apt install vault)
#   - VAULT_ROOT_TOKEN set in environment or .env file
#
# Usage:
#   ./scripts/start-vault-dev.sh
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load .env if it exists
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

# Check if vault CLI is installed
if ! command -v vault &>/dev/null; then
    echo -e "${RED}ERROR: Vault CLI not installed${NC}"
    echo -e "${YELLOW}Install it with:${NC}"
    echo "  macOS:  brew install vault"
    echo "  Ubuntu: sudo apt install vault"
    echo "  Other:  https://developer.hashicorp.com/vault/install"
    exit 1
fi

# Check/generate root token
if [[ -z "${VAULT_ROOT_TOKEN:-}" ]]; then
    echo -e "${YELLOW}VAULT_ROOT_TOKEN not set. Generating one...${NC}"
    VAULT_ROOT_TOKEN=$(./scripts/generate-vault-token.sh)
    echo -e "${GREEN}Generated token: ${VAULT_ROOT_TOKEN}${NC}"
    echo ""
    echo -e "${YELLOW}Add this to your .env file:${NC}"
    echo "VAULT_ROOT_TOKEN=${VAULT_ROOT_TOKEN}"
    echo ""
fi

# Address and port
VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_PORT="${VAULT_PORT:-8200}"

echo -e "${BLUE}=== Starting Vault Dev Server ===${NC}"
echo -e "Address: ${VAULT_ADDR}"
echo -e "Token:   ${VAULT_ROOT_TOKEN:0:8}...${VAULT_ROOT_TOKEN: -4}"
echo ""

# Check if already running
if vault status -address="${VAULT_ADDR}" &>/dev/null 2>&1; then
    echo -e "${YELLOW}Vault is already running at ${VAULT_ADDR}${NC}"
    echo -e "To stop it: pkill vault"
    exit 0
fi

# Start Vault in dev mode
echo -e "${GREEN}Starting Vault...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Run Vault dev server
# -dev enables dev mode with in-memory storage
# -dev-root-token-id sets the root token
# -dev-listen-address sets the listen address (localhost only for security)
exec vault server \
    -dev \
    -dev-root-token-id="${VAULT_ROOT_TOKEN}" \
    -dev-listen-address="127.0.0.1:${VAULT_PORT}"

#!/usr/bin/env bash
#
# Vault Setup Script for Kali Personal Assistant
# 
# This script configures HashiCorp Vault with:
# - KV v2 secrets engine
# - AppRole authentication for each service (nuxt, python-ai, livekit)
# - Least-privilege policies for each service
#
# Supports both:
# - Local Vault (installed on host) - preferred for development
# - Docker Vault (vault-dev container) - if local not available
#
# SECURITY NOTES:
# - Run this ONLY on initial setup
# - Save the generated credentials securely
# - NEVER commit credentials to git
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_CONTAINER="${VAULT_CONTAINER:-vault-dev}"

# Detect if we should use local or Docker Vault
USE_LOCAL_VAULT=false

detect_vault_mode() {
    # Check if local vault CLI is availaf command -v vault &>/dev/null; then
        if vault status -address="$ble and Vault is running locally
    i{VAULT_ADDR}" &>/dev/null 2>&1; then
            USE_LOCAL_VAULT=true
            echo -e "${GREEN}Detected local Vault installation${NC}"
            return 0
        fi
    fi
    
    # Check if Docker container is running
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${VAULT_CONTAINER}$"; then
        USE_LOCAL_VAULT=false
        echo -e "${GREEN}Detected Docker Vault container: ${VAULT_CONTAINER}${NC}"
        return 0
    fi
    
    echo -e "${RED}ERROR: No Vault instance found!${NC}"
    echo -e "${YELLOW}Either:${NC}"
    echo -e "  1. Install Vault locally: brew install vault (macOS) or apt install vault (Linux)"
    echo -e "     Then start it: vault server -dev -dev-root-token-id=\${VAULT_ROOT_TOKEN}"
    echo -e "  2. Start Docker Vault: docker compose up -d vault"
    exit 1
}

# Function to run vault commands (adapts to local or Docker)
vault_cmd() {
    if [[ "${USE_LOCAL_VAULT}" == "true" ]]; then
        VAULT_ADDR="${VAULT_ADDR}" VAULT_TOKEN="${VAULT_ROOT_TOKEN}" vault "$@"
    else
        docker exec -e VAULT_ADDR=http://127.0.0.1:8200 \
                    -e VAULT_TOKEN="${VAULT_ROOT_TOKEN}" \
                    "${VAULT_CONTAINER}" \
                    vault "$@"
    fi
}

# Function to pipe data to vault (for policies)
vault_policy_write() {
    local policy_name="$1"
    local policy_content="$2"
    
    if [[ "${USE_LOCAL_VAULT}" == "true" ]]; then
        echo "${policy_content}" | VAULT_ADDR="${VAULT_ADDR}" VAULT_TOKEN="${VAULT_ROOT_TOKEN}" vault policy write "${policy_name}" -
    else
        echo "${policy_content}" | docker exec -i -e VAULT_ADDR=http://127.0.0.1:8200 \
            -e VAULT_TOKEN="${VAULT_ROOT_TOKEN}" \
            "${VAULT_CONTAINER}" \
            vault policy write "${policy_name}" -
    fi
}

# Check if VAULT_ROOT_TOKEN is set
if [[ -z "${VAULT_ROOT_TOKEN:-}" ]]; then
    echo -e "${RED}ERROR: VAULT_ROOT_TOKEN environment variable is not set${NC}"
    echo -e "${YELLOW}Please run: export VAULT_ROOT_TOKEN=\$(./scripts/generate-vault-token.sh)${NC}"
    exit 1
fi

echo -e "${BLUE}=== Vault Setup for Kali Personal Assistant ===${NC}"
echo -e "Using Vault at: ${VAULT_ADDR}"

# Detect which Vault to use
detect_vault_mode

# Wait for Vault to be ready
echo -e "\n${YELLOW}Waiting for Vault to be ready...${NC}"
for i in {1..30}; do
    if [[ "${USE_LOCAL_VAULT}" == "true" ]]; then
        if vault status -address="${VAULT_ADDR}" &>/dev/null; then
            echo -e "${GREEN}Vault is ready!${NC}"
            break
        fi
    else
        if docker exec "${VAULT_CONTAINER}" vault status -address=http://127.0.0.1:8200 &>/dev/null; then
            echo -e "${GREEN}Vault is ready!${NC}"
            break
        fi
    fi
    if [[ $i -eq 30 ]]; then
        echo -e "${RED}ERROR: Vault did not become ready in time${NC}"
        exit 1
    fi
    sleep 1
done

# Enable KV v2 secrets engine (if not already enabled)
echo -e "\n${YELLOW}Configuring secrets engine...${NC}"
if ! vault_cmd secrets list | grep -q "^secret/"; then
    vault_cmd secrets enable -path=secret kv-v2
    echo -e "${GREEN}KV v2 secrets engine enabled at secret/${NC}"
else
    echo -e "${GREEN}KV v2 secrets engine already enabled${NC}"
fi

# Enable AppRole auth method (if not already enabled)
echo -e "\n${YELLOW}Configuring AppRole authentication...${NC}"
if ! vault_cmd auth list | grep -q "^approle/"; then
    vault_cmd auth enable approle
    echo -e "${GREEN}AppRole authentication enabled${NC}"
else
    echo -e "${GREEN}AppRole authentication already enabled${NC}"
fi

# ============================
# Create Policies
# ============================

echo -e "\n${YELLOW}Creating access policies...${NC}"

# Nuxt Admin Policy (web frontend - FULL ACCESS for admin UI)
# This is the ONLY service that can write secrets - used for the config page
NUXT_ADMIN_POLICY='# Nuxt Admin Policy
# Full read/write access for managing secrets via the web frontend
# This is the administrative interface for configuring all services

# Full access to nuxt-specific secrets
path "secret/data/nuxt" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/data/nuxt/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/nuxt" {
  capabilities = ["read", "list", "delete"]
}

path "secret/metadata/nuxt/*" {
  capabilities = ["read", "list", "delete"]
}

# Full access to shared secrets (API keys managed here)
path "secret/data/shared" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/data/shared/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/shared" {
  capabilities = ["read", "list", "delete"]
}

path "secret/metadata/shared/*" {
  capabilities = ["read", "list", "delete"]
}

# Full access to python-ai secrets (configured from web UI)
path "secret/data/python-ai" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/data/python-ai/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/python-ai" {
  capabilities = ["read", "list", "delete"]
}

path "secret/metadata/python-ai/*" {
  capabilities = ["read", "list", "delete"]
}

# Full access to livekit secrets (configured from web UI)
path "secret/data/livekit" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/data/livekit/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/livekit" {
  capabilities = ["read", "list", "delete"]
}

path "secret/metadata/livekit/*" {
  capabilities = ["read", "list", "delete"]
}

# Full access to database secrets (configured from web UI)
path "secret/data/databases" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/data/databases/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/databases" {
  capabilities = ["read", "list", "delete"]
}

path "secret/metadata/databases/*" {
  capabilities = ["read", "list", "delete"]
}

# List all secret paths (for admin UI)
path "secret/metadata" {
  capabilities = ["list"]
}

path "secret/metadata/*" {
  capabilities = ["list"]
}'

vault_policy_write "nuxt-admin-policy" "${NUXT_ADMIN_POLICY}"
echo -e "${GREEN}Created policy: nuxt-admin-policy (ADMIN - read/write)${NC}"

# Python AI Service Policy (READ-ONLY)
PYTHON_AI_POLICY='# Python AI Service Policy
# READ-ONLY access to AI-related secrets
# Secrets are configured via the Nuxt admin UI

# Read-only AI service secrets
path "secret/data/python-ai" {
  capabilities = ["read"]
}

path "secret/data/python-ai/*" {
  capabilities = ["read"]  
}

# Read-only shared secrets (API keys, etc.)
path "secret/data/shared" {
  capabilities = ["read"]
}

path "secret/data/shared/*" {
  capabilities = ["read"]
}

# Read-only database connection info
path "secret/data/databases" {
  capabilities = ["read"]
}

path "secret/data/databases/*" {
  capabilities = ["read"]
}

# Explicitly deny write access everywhere
path "secret/data/*" {
  capabilities = ["deny"]
  allowed_parameters = {}
}

# Deny metadata write access
path "secret/metadata/*" {
  capabilities = ["deny"]
}'

vault_policy_write "python-ai-policy" "${PYTHON_AI_POLICY}"
echo -e "${GREEN}Created policy: python-ai-policy (READ-ONLY)${NC}"

# LiveKit Voice Service Policy (READ-ONLY)
LIVEKIT_POLICY='# LiveKit Voice Service Policy
# READ-ONLY access to voice/video related secrets
# Secrets are configured via the Nuxt admin UI

# Read-only livekit secrets
path "secret/data/livekit" {
  capabilities = ["read"]
}

path "secret/data/livekit/*" {
  capabilities = ["read"]
}

# Read-only shared secrets
path "secret/data/shared" {
  capabilities = ["read"]
}

path "secret/data/shared/*" {
  capabilities = ["read"]
}

# Explicitly deny write access everywhere
path "secret/data/*" {
  capabilities = ["deny"]
  allowed_parameters = {}
}

# Deny metadata write access
path "secret/metadata/*" {
  capabilities = ["deny"]
}'

vault_policy_write "livekit-policy" "${LIVEKIT_POLICY}"
echo -e "${GREEN}Created policy: livekit-policy (READ-ONLY)${NC}"

# ============================
# Create AppRoles
# ============================

echo -e "\n${YELLOW}Creating AppRoles...${NC}"

# Helper function to create an AppRole and get credentials
create_approle() {
    local role_name="$1"
    local policy="$2"
    local token_ttl="${3:-1h}"
    local token_max_ttl="${4:-4h}"
    
    echo -e "\n${BLUE}Creating AppRole: ${role_name}${NC}"
    
    # Create the role
    vault_cmd write "auth/approle/role/${role_name}" \
        token_policies="${policy}" \
        token_ttl="${token_ttl}" \
        token_max_ttl="${token_max_ttl}" \
        secret_id_num_uses=0 \
        secret_id_ttl=0
    
    # Get the role ID
    local role_id
    role_id=$(vault_cmd read -field=role_id "auth/approle/role/${role_name}/role-id")
    
    # Generate a secret ID
    local secret_id
    secret_id=$(vault_cmd write -f -field=secret_id "auth/approle/role/${role_name}/secret-id")
    
    echo -e "${GREEN}AppRole created: ${role_name}${NC}"
    echo "  Role ID:   ${role_id}"
    echo "  Secret ID: ${secret_id}"
    
    # Return values (store in variables)
    # Convert dashes to underscores for valid bash variable names
    local var_name="${role_name^^}"
    var_name="${var_name//-/_}"
    eval "${var_name}_ROLE_ID='${role_id}'"
    eval "${var_name}_SECRET_ID='${secret_id}'"
}

# Create AppRoles for each service
# Note: nuxt-admin has WRITE access, others are READ-ONLY
create_approle "nuxt-admin" "nuxt-admin-policy" "1h" "24h"
create_approle "python-ai" "python-ai-policy" "1h" "24h"
create_approle "livekit" "livekit-policy" "1h" "24h"

# ============================
# Initialize Default Secrets
# ============================

echo -e "\n${YELLOW}Initializing default secret paths...${NC}"

# Generate random secrets for initialization
RANDOM_SECRET_1=$(openssl rand -hex 16)
RANDOM_SECRET_2=$(openssl rand -hex 16)

# Initialize secrets at each path
vault_cmd kv put secret/nuxt \
    better-auth-secret="changeme-${RANDOM_SECRET_1}" \
    session-secret="changeme-${RANDOM_SECRET_2}" \
    initialized="true"

vault_cmd kv put secret/python-ai \
    openai-api-key="sk-changeme" \
    anthropic-api-key="sk-ant-changeme" \
    google-api-key="changeme" \
    initialized="true"

vault_cmd kv put secret/livekit \
    api-key="devkey" \
    api-secret="secret" \
    initialized="true"

vault_cmd kv put secret/shared \
    resend-api-key="re_changeme" \
    initialized="true"

vault_cmd kv put secret/databases \
    neo4j-uri="bolt://localhost:7687" \
    neo4j-username="neo4j" \
    neo4j-password="password" \
    mongodb-uri="mongodb://kali:kalipassword@localhost:27017" \
    redis-url="redis://localhost:6379/0" \
    initialized="true"

echo -e "${GREEN}Default secrets initialized${NC}"

# ============================
# Generate .env Credentials File
# ============================

echo -e "\n${YELLOW}Generating credentials file...${NC}"

CREDS_FILE=".vault-credentials.env"

cat > "${CREDS_FILE}" << EOF
# Vault Credentials - Generated $(date)
# 
# ⚠️  SECURITY WARNING: Do NOT commit this file to git!
# Add .vault-credentials.env to your .gitignore
#
# Vault Mode: $(if [[ "${USE_LOCAL_VAULT}" == "true" ]]; then echo "Local"; else echo "Docker"; fi)
#
# Permission Model:
#   - nuxt-admin: READ/WRITE (admin UI for managing all secrets)
#   - python-ai:  READ-ONLY  (consumes secrets configured via web UI)
#   - livekit:    READ-ONLY  (consumes secrets configured via web UI)
#

# ============================
# Vault Address
# ============================
# For local development (services running on host):
VAULT_ADDR=http://127.0.0.1:8200
# For Docker services (services running in containers):
# VAULT_ADDR=http://vault-dev:8200

# ============================
# Root Token (for emergency admin operations only)
# ============================
VAULT_ROOT_TOKEN=${VAULT_ROOT_TOKEN}

# ============================
# Nuxt Admin Credentials (READ/WRITE - Admin UI)
# ============================
NUXT_VAULT_ROLE_ID=${NUXT_ADMIN_ROLE_ID}
NUXT_VAULT_SECRET_ID=${NUXT_ADMIN_SECRET_ID}

# ============================
# Python AI Service Credentials (READ-ONLY)
# ============================
PYTHON_AI_VAULT_ROLE_ID=${PYTHON_AI_ROLE_ID}
PYTHON_AI_VAULT_SECRET_ID=${PYTHON_AI_SECRET_ID}

# ============================
# LiveKit Service Credentials (READ-ONLY)
# ============================
LIVEKIT_VAULT_ROLE_ID=${LIVEKIT_ROLE_ID}
LIVEKIT_VAULT_SECRET_ID=${LIVEKIT_SECRET_ID}
EOF

chmod 600 "${CREDS_FILE}"
echo -e "${GREEN}Credentials saved to: ${CREDS_FILE}${NC}"

# ============================
# Summary
# ============================

echo -e "\n${GREEN}=== Setup Complete ===${NC}"

if [[ "${USE_LOCAL_VAULT}" == "true" ]]; then
    echo -e "
${YELLOW}Using LOCAL Vault - Great for development!${NC}

${YELLOW}Permission Model:${NC}
  ${GREEN}nuxt-admin${NC}: READ/WRITE (admin UI for managing secrets)
  ${BLUE}python-ai${NC}:  READ-ONLY  (consumes AI secrets)
  ${BLUE}livekit${NC}:    READ-ONLY  (consumes voice secrets)

${YELLOW}Next Steps:${NC}

1. ${BLUE}Copy credentials to your .env files:${NC}
   cat ${CREDS_FILE}

2. ${BLUE}Test the admin AppRole login (has write access):${NC}
   vault write auth/approle/login \\
     role_id=\"${NUXT_ADMIN_ROLE_ID}\" \\
     secret_id=\"${NUXT_ADMIN_SECRET_ID}\"

3. ${BLUE}View secrets:${NC}
   vault kv get secret/nuxt
   vault kv get secret/python-ai

4. ${BLUE}Secrets will be configured via the Nuxt admin UI${NC}
   (or manually via Vault CLI for initial setup)
"
else
    echo -e "
${YELLOW}Using DOCKER Vault${NC}

${YELLOW}Permission Model:${NC}
  ${GREEN}nuxt-admin${NC}: READ/WRITE (admin UI for managing secrets)
  ${BLUE}python-ai${NC}:  READ-ONLY  (consumes AI secrets)
  ${BLUE}livekit${NC}:    READ-ONLY  (consumes voice secrets)

${YELLOW}Next Steps:${NC}

1. ${BLUE}Copy credentials to your .env files:${NC}
   cat ${CREDS_FILE}

2. ${BLUE}Test the admin AppRole login (has write access):${NC}
   docker exec -e VAULT_ADDR=http://127.0.0.1:8200 vault-dev \\
     vault write auth/approle/login \\
       role_id=\"${NUXT_ADMIN_ROLE_ID}\" \\
       secret_id=\"${NUXT_ADMIN_SECRET_ID}\"

3. ${BLUE}View secrets:${NC}
   docker exec -e VAULT_TOKEN=${VAULT_ROOT_TOKEN} vault-dev vault kv get secret/nuxt

4. ${BLUE}Secrets will be configured via the Nuxt admin UI${NC}
   (or manually via Vault CLI for initial setup)
"
fi

echo -e "${RED}⚠️  IMPORTANT: Keep ${CREDS_FILE} secure and NEVER commit it to git!${NC}"

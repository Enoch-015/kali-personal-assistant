# HashiCorp Vault Setup Guide

This document explains how to securely configure HashiCorp Vault for the Kali Personal Assistant project.

## ⚠️ Security Overview

**Never use predictable root tokens like `myroot`!**

This setup uses:
- **Random root token** - Generated cryptographically, stored in `.env`
- **Localhost binding** - Vault only accessible from `127.0.0.1`
- **AppRole authentication** - Each service gets its own credentials
- **Least-privilege policies** - Services can only access their own secrets
- **Secret caching** - Reduces Vault calls, improves performance

## Two Options: Local or Docker

| Option | Best For | Pros | Cons |
|--------|----------|------|------|
| **Local Vault** | Day-to-day development | Fast startup, no Docker overhead, easier debugging | Requires Vault CLI install |
| **Docker Vault** | CI/CD, team consistency | No install needed, isolated | Slower startup, Docker dependency |

---

## Option A: Local Vault (Recommended for Dev)

### 1. Install Vault CLI

```bash
# macOS
brew install vault

# Ubuntu/Debian
sudo apt update && sudo apt install vault

# Other Linux / Manual
# Download from: https://developer.hashicorp.com/vault/install
```

Verify installation:
```bash
vault --version
# Vault v1.x.x
```

### 2. Generate a Secure Root Token

```bash
# Generate token
export VAULT_ROOT_TOKEN=$(./scripts/generate-vault-token.sh)

# Save to .env file
echo "VAULT_ROOT_TOKEN=${VAULT_ROOT_TOKEN}" >> .env
```

### 3. Start Vault Dev Server

**Option A: Use the helper script (runs in foreground)**
```bash
./scripts/start-vault-dev.sh
```

**Option B: Start manually in background**
```bash
# Start in background
vault server -dev \
  -dev-root-token-id="${VAULT_ROOT_TOKEN}" \
  -dev-listen-address="127.0.0.1:8200" &

# Or if you want to see logs
vault server -dev \
  -dev-root-token-id="${VAULT_ROOT_TOKEN}" \
  -dev-listen-address="127.0.0.1:8200"
```

### 4. Set Environment and Run Setup

```bash
# In a new terminal
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="${VAULT_ROOT_TOKEN}"

# Verify Vault is running
vault status

# Run the setup script
./scripts/setup-vault.sh
```

### 5. Working with Local Vault

```bash
# Set these in your shell (add to ~/.bashrc or ~/.zshrc for persistence)
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="your-root-token-here"

# List secrets
vault kv list secret/

# Read a secret
vault kv get secret/python-ai

# Update a secret
vault kv patch secret/python-ai openai-api-key="sk-your-real-key"

# Add a new key to existing secret
vault kv patch secret/shared new-api-key="value"
```

### Stopping Local Vault

```bash
# If running in foreground: Ctrl+C

# If running in background
pkill vault

# Or find and kill
ps aux | grep vault
kill <pid>
```

---

## Option B: Docker Vault

### 1. Generate a Secure Root Token

```bash
# Generate and save to .env
export VAULT_ROOT_TOKEN=$(./scripts/generate-vault-token.sh)
echo "VAULT_ROOT_TOKEN=${VAULT_ROOT_TOKEN}" >> .env
```

### 2. Start Vault Container

```bash
docker compose up -d vault
```

### 3. Run Setup Script

```bash
./scripts/setup-vault.sh
```

The script auto-detects Docker mode when local Vault isn't running.

### 4. Working with Docker Vault

```bash
# Read a secret
docker exec -e VAULT_TOKEN=$VAULT_ROOT_TOKEN vault-dev \
  vault kv get secret/python-ai

# Update a secret
docker exec -e VAULT_TOKEN=$VAULT_ROOT_TOKEN vault-dev \
  vault kv patch secret/python-ai openai-api-key="sk-your-real-key"

# Shell into container for multiple commands
docker exec -it vault-dev sh
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="your-token"
vault kv list secret/
```

---

## After Setup: Configure Your Services

### 1. Copy Credentials

The setup script generates `.vault-credentials.env`:

```bash
cat .vault-credentials.env
```

Copy the relevant values to your service `.env` files:

**apps/web/.env:**
```bash
VAULT_ADDR=http://127.0.0.1:8200
VAULT_ROLE_ID=<from NUXT_VAULT_ROLE_ID>
VAULT_SECRET_ID=<from NUXT_VAULT_SECRET_ID>
```

**apps/ai/.env:**
```bash
VAULT_ADDR=http://127.0.0.1:8200
VAULT_ROLE_ID=<from PYTHON_AI_VAULT_ROLE_ID>
VAULT_SECRET_ID=<from PYTHON_AI_VAULT_SECRET_ID>
```

**apps/voice/.env:**
```bash
VAULT_ADDR=http://127.0.0.1:8200
VAULT_ROLE_ID=<from LIVEKIT_VAULT_ROLE_ID>
VAULT_SECRET_ID=<from LIVEKIT_VAULT_SECRET_ID>
```

### 2. Update Real Secrets

Replace placeholder values with your actual API keys:

```bash
# For local Vault
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="$VAULT_ROOT_TOKEN"

vault kv patch secret/python-ai \
  openai-api-key="sk-your-real-key" \
  anthropic-api-key="sk-ant-your-real-key" \
  google-api-key="your-google-key"

vault kv patch secret/shared \
  resend-api-key="re_your-real-key"

vault kv patch secret/livekit \
  api-key="your-livekit-key" \
  api-secret="your-livekit-secret"
```

---

## Architecture

### Permission Model

This setup implements a **centralized admin model** where:
- **Nuxt/Web** (nuxt-admin) = **READ/WRITE** - Admin interface for managing ALL secrets via web UI
- **Python AI** = **READ-ONLY** - Consumes secrets configured via the admin UI
- **LiveKit** = **READ-ONLY** - Consumes secrets configured via the admin UI

```
┌─────────────────────────────────────────────────────────────────┐
│                        HashiCorp Vault                          │
├─────────────────────────────────────────────────────────────────┤
│  secret/nuxt       │  secret/shared   │  secret/python-ai       │
│  secret/livekit    │  secret/databases│                         │
└─────────────────────────────────────────────────────────────────┘
          ▲                    ▲                    ▲
          │                    │                    │
    ┌─────┴─────┐        ┌────┴────┐         ┌────┴────┐
    │ nuxt-admin│        │python-ai│         │ livekit │
    │ READ/WRITE│        │READ-ONLY│         │READ-ONLY│
    └───────────┘        └─────────┘         └─────────┘
          │
          │ Admin API (/api/admin/secrets/*)
          ▼
    ┌───────────┐
    │  Web UI   │ (Config page - you'll create this)
    └───────────┘
```

### Secret Paths

| Path | Description | Nuxt Admin | Python AI | LiveKit |
|------|-------------|:----------:|:---------:|:-------:|
| `secret/nuxt` | Nuxt-specific secrets | ✅ R/W | ❌ | ❌ |
| `secret/shared` | Shared API keys | ✅ R/W | ✅ Read | ✅ Read |
| `secret/python-ai` | AI service secrets | ✅ R/W | ✅ Read | ❌ |
| `secret/livekit` | Voice service secrets | ✅ R/W | ❌ | ✅ Read |
| `secret/databases` | Database credentials | ✅ R/W | ✅ Read | ❌ |

---

## Admin API Endpoints

The Nuxt web app exposes admin endpoints for managing secrets:

### List Available Paths

```bash
GET /api/admin/secrets

# Response:
{
  "success": true,
  "paths": [...],
  "availablePaths": [
    { "path": "nuxt", "description": "Nuxt-specific secrets" },
    { "path": "shared", "description": "Shared API keys" },
    ...
  ]
}
```

### Read Secrets

```bash
GET /api/admin/secrets/:path
GET /api/admin/secrets/python-ai?masked=true  # Default: masked

# Response:
{
  "success": true,
  "path": "python-ai",
  "secrets": { "openai-api-key": "sk-p****" },
  "masked": true,
  "keys": ["openai-api-key", "anthropic-api-key"]
}
```

### Update Secrets (Merge)

```bash
PATCH /api/admin/secrets/:path
Content-Type: application/json

{
  "secrets": {
    "openai-api-key": "sk-new-key-here",
    "new-key": "new-value"
  }
}

# To delete a key, set its value to null:
{
  "secrets": {
    "old-key": null
  }
}
```

### Replace All Secrets

```bash
PUT /api/admin/secrets/:path
Content-Type: application/json

{
  "secrets": {
    "key1": "value1",
    "key2": "value2"
  }
}

# ⚠️ WARNING: This overwrites ALL existing secrets at this path!
```

### Delete Secrets

```bash
# Delete a single key
DELETE /api/admin/secrets/:path?key=openai-api-key

# Delete entire path (requires confirmation)
DELETE /api/admin/secrets/:path?confirm=true
```

---

## Usage in Code

### Python Services (AI/Voice) - READ-ONLY

```python
from config import get_vault_client

async def get_openai_key():
    client = await get_vault_client()
    return await client.get_openai_api_key()

# Or read all secrets for a path
async def get_ai_config():
    client = await get_vault_client()
    secrets = await client.get_ai_secrets()
    return {
        "openai_key": secrets.get("openai-api-key"),
        "anthropic_key": secrets.get("anthropic-api-key"),
    }

# NOTE: Write operations will fail with "permission denied"
# All secret management is done via the Nuxt admin UI
```

### Nuxt (TypeScript) - READ/WRITE

```typescript
// Reading secrets - auto-injected via plugin
export default defineEventHandler(async (event) => {
  const secrets = event.context.vault;
  const apiKey = secrets?.shared?.['resend-api-key'];
  // Use apiKey...
});

// Writing secrets - use admin helper functions
import { updateSecretKey, updateSecrets } from '~/server/utils/vault';

// Update a single key
await updateSecretKey('python-ai', 'openai-api-key', 'sk-new-key');

// Update multiple keys (merge)
await updateSecrets('shared', {
  'resend-api-key': 're_new_key',
  'other-api-key': 'new-value',
});

// Or use the vault client directly
import { getVaultClient } from '~/server/utils/vault';

const client = getVaultClient();
const secrets = await client.getSecret('nuxt');
```

---

## Environment Variable Reference

### Root `.env`

```bash
# Required for Vault dev mode (local or Docker)
VAULT_ROOT_TOKEN=<64-char-hex-token>
```

### Service `.env` Files

```bash
# Vault address (localhost for local dev)
VAULT_ADDR=http://127.0.0.1:8200

# For Docker-to-Docker networking (when services run in containers)
# VAULT_ADDR=http://vault-dev:8200

# Service-specific AppRole credentials
VAULT_ROLE_ID=<from .vault-credentials.env>
VAULT_SECRET_ID=<from .vault-credentials.env>
```

---

## Development Workflow

### Daily Development

1. **Start Vault** (if not already running):
   ```bash
   # Local (simpler for dev)
   ./scripts/start-vault-dev.sh
   
   # Or Docker
   docker compose up -d vault
   ```

2. **Start your services normally**:
   ```bash
   # Nuxt
   cd apps/web && pnpm dev
   
   # Python AI
   cd apps/ai && python -m uvicorn src.main:app --reload
   ```

3. **Secrets are auto-loaded** from Vault via AppRole authentication.

### Adding New Secrets

```bash
# Set environment
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="$VAULT_ROOT_TOKEN"

# Add to existing path
vault kv patch secret/python-ai new-secret-key="value"

# Or create a new secret path (update policies to grant access)
vault kv put secret/new-service api-key="value"
```

### Rotate AppRole Secret IDs

```bash
# Generate new secret ID for a service
vault write -f auth/approle/role/nuxt-admin/secret-id
vault write -f auth/approle/role/python-ai/secret-id
vault write -f auth/approle/role/livekit/secret-id

# Update the appropriate .env with the new secret ID
```

---

## Security Best Practices

### ✅ Do

- Generate random root tokens with `./scripts/generate-vault-token.sh`
- Store credentials in `.env` files (git-ignored)
- Use AppRole authentication (not root token) in services
- Rotate secret IDs periodically
- Set short token TTLs (1 hour default)

### ❌ Don't

- Use predictable tokens like `myroot`, `root`, `dev`
- Commit `.env` or `.vault-credentials.env` to git
- Use root token in production services
- Expose port 8200 to the public internet
- Log secret values

---

## Troubleshooting

### Check Vault Status

```bash
# Local
vault status

# Docker
docker exec vault-dev vault status
```

### "Connection refused" Error

Vault isn't running. Start it:
```bash
# Local
./scripts/start-vault-dev.sh

# Docker
docker compose up -d vault
```

### "Permission denied" Error

Your AppRole doesn't have access to that path. Check the policy:
```bash
vault policy read nuxt-admin-policy
vault policy read python-ai-policy
vault policy read livekit-policy
```

> **Note:** Python AI and LiveKit roles are READ-ONLY by design.
> Write operations will always fail - use the Nuxt admin API instead.

### Test AppRole Login

```bash
vault write auth/approle/login \
  role_id="<your-role-id>" \
  secret_id="<your-secret-id>"
```

### Reset Everything

```bash
# Stop Vault
pkill vault  # local
# or
docker compose down vault  # Docker

# Remove credentials
rm .vault-credentials.env

# Regenerate token
export VAULT_ROOT_TOKEN=$(./scripts/generate-vault-token.sh)
echo "VAULT_ROOT_TOKEN=${VAULT_ROOT_TOKEN}" > .env

# Start fresh
./scripts/start-vault-dev.sh  # in one terminal
./scripts/setup-vault.sh      # in another terminal
```

---

## Production Considerations

For production deployments:

1. **Don't use dev mode** - Use proper Vault with TLS and auto-unseal
2. **Enable audit logging** - Track all secret access
3. **Use short-lived tokens** - 1 hour TTL or less
4. **Set CIDR restrictions** - Limit where AppRoles can authenticate from
5. **Use Vault Agent** - For automatic token renewal
6. **Consider Vault Enterprise** - For namespaces and enterprise features

See [HashiCorp Vault Production Hardening](https://www.vaultproject.io/docs/concepts/production-hardening) for more details.

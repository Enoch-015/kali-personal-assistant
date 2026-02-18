#!/usr/bin/env bash
#
# Generate a cryptographically secure root token for Vault
# 
# Usage:
#   ./scripts/generate-vault-token.sh           # Print to stdout
#   ./scripts/generate-vault-token.sh --export  # Export to current shell
#

set -euo pipefail

# Generate a 32-byte hex token (64 characters)
TOKEN=$(openssl rand -hex 32)

case "${1:-}" in
    --export)
        echo "export VAULT_ROOT_TOKEN='${TOKEN}'"
        echo ""
        echo "# Run: eval \$(./scripts/generate-vault-token.sh --export)"
        ;;
    --help|-h)
        echo "Generate a secure random token for Vault"
        echo ""
        echo "Usage:"
        echo "  $0           Print token to stdout"
        echo "  $0 --export  Print export command (use with eval)"
        echo ""
        echo "Example:"
        echo "  # Set in current shell"
        echo "  eval \$($0 --export)"
        echo ""
        echo "  # Or save to .env file"
        echo "  echo \"VAULT_ROOT_TOKEN=\$($0)\" >> .env"
        ;;
    *)
        echo "${TOKEN}"
        ;;
esac

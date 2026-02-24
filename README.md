# Kali Personal Assistant

A monorepo containing the Nuxt.js frontend, FastAPI AI service, LiveKit voice agent, and shared configuration for the Kali Personal Assistant application.

## 📚 Documentation

Detailed documentation is available in the [`docs/`](docs/) folder:

- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Command cheat sheet
- **[Monorepo Setup Guide](docs/MONOREPO_SETUP.md)** - Detailed setup instructions
- **[VS Code Configuration](docs/VSCODE_SETUP.md)** - Fix TypeScript/ESLint issues
- **[Vercel Configuration](docs/VERCEL_SETUP.md)** - Vercel dashboard setup
- **[GitHub Environments](docs/GITHUB_ENVIRONMENTS.md)** - GitHub secrets management
- **[Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)** - Pre-deployment verification
- **[Config Architecture](docs/CONFIG_ARCHITECTURE.md)** - Shared config layer design
- **[Vault Setup](docs/VAULT_SETUP.md)** - HashiCorp Vault configuration

## 📁 Project Structure

```
kali-personal-assistant/
├── apps/
│   ├── web/          # Nuxt.js frontend application
│   ├── ai/           # FastAPI + LangGraph AI orchestration service
│   ├── voice/        # LiveKit voice agent
│   └── config/       # Shared configuration layer (Vault, providers, settings)
├── docs/             # Project documentation
├── scripts/          # Setup and utility scripts
├── .github/
│   └── workflows/    # CI/CD workflows
├── docker-compose.yaml
├── package.json      # Root package.json for monorepo
└── pnpm-workspace.yaml
```

## 🚀 Getting Started

### Prerequisites

- Node.js 20+
- pnpm 9+
- Python 3.11+
- Docker & Docker Compose (for local infrastructure)

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd kali-personal-assistant
```

2. Install Node.js dependencies:
```bash
pnpm install
```

3. Set up Python environment for the AI service:
```bash
cd apps/ai
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..
```

4. Configure environment variables:
```bash
# Copy the root example env file and fill in your credentials
cp .env.example .env
# Also copy the web-specific env file
cp apps/web/.env.example apps/web/.env
```

5. Start local infrastructure (Redis, Neo4j, MongoDB, Vault, LiveKit):
```bash
docker compose up -d
```

See [`docs/VAULT_SETUP.md`](docs/VAULT_SETUP.md) and the scripts in `scripts/` for Vault initialisation.

## 🛠️ Development

### Run Web App (Nuxt)
```bash
pnpm dev
# or
pnpm --filter web dev
```

The web app will be available at http://localhost:3000

### Run AI Service (FastAPI)
```bash
pnpm dev:ai
# or
cd apps/ai && uvicorn src.main:app --reload
```

The AI service will be available at:
- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Run Web App and AI Service Simultaneously
```bash
pnpm dev:all
```

## 🏗️ Infrastructure Services

The `docker-compose.yaml` provides all required backing services for local development:

| Service | Purpose | Default Port |
|---|---|---|
| Redis | Event bus & caching | 6379 |
| Neo4j | Graphiti memory graph | 7474 (browser), 7687 (Bolt) |
| MongoDB | Sessions, transcripts & policy store | 27017 |
| Vault | Secrets management | 8200 |
| LiveKit | Real-time voice/media server | 7880 |
| Redis Insight | Redis GUI (optional) | 8001 |

```bash
# Start all infrastructure services
docker compose up -d

# Start only specific services
docker compose up -d redis neo4j mongodb
```

## 🧪 Testing & Linting

### Lint Web App
```bash
pnpm lint           # Check for issues
pnpm lint:fix       # Auto-fix issues
```

### Build

```bash
# Build web app
pnpm build

# Build AI service (validation only)
pnpm build:ai
```

## 🚢 Deployment

### Web App (Vercel)

The web app automatically deploys to Vercel when changes are pushed to `apps/web/` on the main branch.

**⚠️ IMPORTANT: Configure Vercel Dashboard First!**

Since your entire repo is connected to Vercel, you MUST set the **Root Directory** in Vercel:

1. Go to Vercel Dashboard → Your Project → Settings → General
2. Set **Root Directory** to: `apps/web`
3. Save changes

See [`docs/VERCEL_SETUP.md`](docs/VERCEL_SETUP.md) for complete instructions.

**Required GitHub Secrets:**

You must create a **`production` environment** in GitHub and add these secrets:

1. Go to: GitHub Repo → Settings → Environments → New environment
2. Name it: `production`
3. Add the following secrets:
   - `VERCEL_TOKEN`
   - `VERCEL_ORG_ID`
   - `VERCEL_PROJECT_ID`
   - `TURSO_DATABASE_URL`
   - `TURSO_AUTH_TOKEN`
   - `BETTER_AUTH_SECRET`
   - `BETTER_AUTH_BASE_URL`
   - `RESEND_API_KEY`
   - `RESEND_FROM_EMAIL`

See [`docs/GITHUB_ENVIRONMENTS.md`](docs/GITHUB_ENVIRONMENTS.md) for more details on environment secrets.

### AI Service (Manual or Custom)

See [`apps/ai/README.md`](apps/ai/README.md) for AI service deployment instructions.

## 📝 Workflow Triggers

- **Deploy Web**: Triggers only when `apps/web/**` files change
- **Test AI**: Triggers only when `apps/ai/**` files change
- Changes to Python code **will not** trigger Vercel deployment
- Changes to Nuxt code **will not** trigger AI service tests

All secrets are managed through the `production` environment in GitHub.

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run linting and tests
4. Submit a pull request

## 📄 License

[Your License Here]

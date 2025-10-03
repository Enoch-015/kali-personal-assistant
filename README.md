# Ka## 📚 Documentation

Detailed documentation is available in the [`docs/`](docs/) folder:

- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Command cheat sheet
- **[Monorepo Setup Guide](docs/MONOREPO_SETUP.md)** - Detailed setup instructions
- **[VS Code Configuration](docs/VSCODE_SETUP.md)** - Fix TypeScript/ESLint issues
- **[Vercel Configuration](docs/VERCEL_SETUP.md)** - Vercel dashboard setup
- **[GitHub Environments](docs/GITHUB_ENVIRONMENTS.md)** - GitHub secrets management
- **[Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)** - Pre-deployment verificationnal Assistant

A monorepo containing both the Nuxt.js frontend and FastAPI backend for the Kali Personal Assistant application.

## � Documentation

Detailed documentation is available in the [`docs/`](docs/) folder:

- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Command cheat sheet
- **[Monorepo Setup Guide](docs/MONOREPO_SETUP.md)** - Detailed setup instructions
- **[Vercel Configuration](docs/VERCEL_SETUP.md)** - Vercel dashboard setup
- **[Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)** - Pre-deployment verification

## �📁 Project Structure

```
kali-personal-assistant/
├── apps/
│   ├── web/          # Nuxt.js frontend application
│   └── api/          # FastAPI backend application
├── .github/
│   └── workflows/    # CI/CD workflows
├── package.json      # Root package.json for monorepo
└── pnpm-workspace.yaml
```

## 🚀 Getting Started

### Prerequisites

- Node.js 20+
- pnpm 9+
- Python 3.11+

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd kali-personal-assistant
```

2. Install dependencies:
```bash
# Install Node.js dependencies for web app
pnpm install
```

3. Set up Python environment for API:
```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..
```

4. Configure environment variables:
```bash
# Copy example env files and update them
cp apps/web/.env.example apps/web/.env
# Edit apps/web/.env with your credentials
```

## 🛠️ Development

### Run Web App (Nuxt)
```bash
pnpm dev
# or
pnpm --filter web dev
```

The web app will be available at http://localhost:3000

### Run API (FastAPI)
```bash
pnpm dev:api
# or
cd apps/api && uvicorn src.main:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Run Both Simultaneously
```bash
pnpm dev:all
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

# Build API (validation only)
pnpm build:api
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

**Why Environment Secrets?**
- Better organization and access control
- Separate secrets per environment (production, staging, etc.)
- Required approvals before deployment (optional)
- Audit trail of deployments

### API (Manual or Custom)

See `apps/api/README.md` for API deployment instructions.

## 📝 Workflow Triggers

- **Deploy Web**: Triggers only when `apps/web/**` files change
- **Test API**: Triggers only when `apps/api/**` files change
- Changes to Python code **will not** trigger Vercel deployment
- Changes to Nuxt code **will not** trigger API tests

All secrets are managed through the `production` environment in GitHub.

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run linting and tests
4. Submit a pull request

## 📄 License

[Your License Here]

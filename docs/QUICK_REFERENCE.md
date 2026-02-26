# Quick Reference - Monorepo Commands

## 🚀 Daily Development

```bash
# Start web app (from root)
pnpm dev

# Start API (from root)
pnpm dev:api

# Start both (from root)
pnpm dev:all
```

## 🧪 Testing & Quality

```bash
# Lint Nuxt app
pnpm lint

# Auto-fix Nuxt lint issues
pnpm lint:fix
```

## 📦 Building

```bash
# Build web for production
pnpm build

# Build/validate API
pnpm build:api
```

## 📂 Working in Specific Apps

```bash
# Web app commands
cd apps/web
pnpm dev
pnpm build
pnpm lint

# API commands
cd apps/api
pip install -r requirements.txt
uvicorn src.main:app --reload
```

## 🔄 Git Workflow

```bash
# Only trigger API tests (NO Vercel deployment)
git add apps/api/**
git commit -m "feat(api): add new endpoint"
git push

# Only trigger Vercel deployment
git add apps/web/**
git commit -m "feat(web): update UI"
git push
```

## 📊 What Triggers What

| Change Location | Runs ESLint? | Deploys to Vercel? | Runs Python Tests? |
|----------------|--------------|-------------------|-------------------|
| `apps/web/**` | ✅ Yes | ✅ Yes | ❌ No |
| `apps/api/**` | ❌ No | ❌ No | ✅ Yes |
| Root files | ❌ No | ❌ No | ❌ No |

## 🔑 Required Secrets (for GitHub Actions)

Add these in: GitHub Repo → Settings → Secrets → Actions

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `NEON_DATABASE_URL`
- `BETTER_AUTH_SECRET`
- `BETTER_AUTH_BASE_URL`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`

## 🐍 Python Setup (First Time)

```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 📝 URLs

- **Web (Dev)**: http://localhost:3000
- **API (Dev)**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

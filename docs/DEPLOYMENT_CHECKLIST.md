# Monorepo Deployment Checklist

Use this checklist to ensure your monorepo is properly configured for deployment.

## ✅ Vercel Configuration

### Dashboard Settings (REQUIRED)
- [ ] Set **Root Directory** to `apps/web` in Vercel Dashboard
  - Path: Vercel → Project → Settings → General → Root Directory
  
- [ ] Configure **Ignored Build Step** for path filtering
  - Path: Vercel → Project → Settings → Git → Ignored Build Step
  - Command: `git diff --quiet HEAD^ HEAD -- apps/web/`
  
- [ ] Add **Environment Variables** in Vercel
  - [ ] `NEON_DATABASE_URL`
  - [ ] `BETTER_AUTH_SECRET`
  - [ ] `BETTER_AUTH_BASE_URL`
  - [ ] `RESEND_API_KEY`
  - [ ] `RESEND_FROM_EMAIL`
  - [ ] `NODE_ENV=production`

## ✅ GitHub Actions Configuration

### GitHub Environment Setup (REQUIRED)
- [ ] Create `production` environment
  - Path: GitHub Repo → Settings → Environments → New environment
  - Name: `production`

### GitHub Environment Secrets (in production environment)
- [ ] `VERCEL_TOKEN` - From https://vercel.com/account/tokens
- [ ] `VERCEL_ORG_ID` - From Vercel project settings
- [ ] `VERCEL_PROJECT_ID` - From Vercel project settings
- [ ] `NEON_DATABASE_URL`
- [ ] `BETTER_AUTH_SECRET`
- [ ] `BETTER_AUTH_BASE_URL`
- [ ] `RESEND_API_KEY`
- [ ] `RESEND_FROM_EMAIL`

### Workflow Files
- [ ] `.github/workflows/deploy-web.yml` exists
- [ ] `.github/workflows/test-api.yml` exists
- [ ] Path filters are configured correctly

## ✅ Repository Configuration

### Root Level
- [ ] `vercel.json` exists with correct config
- [ ] `package.json` has monorepo scripts
- [ ] `pnpm-workspace.yaml` configured
- [ ] `.gitignore` excludes build artifacts

### apps/web
- [ ] `.env` file has all required variables
- [ ] `eslint.config.mjs` ignores `apps/api/**`
- [ ] Package name is `"web"`

### apps/api
- [ ] Python virtual environment created
- [ ] `requirements.txt` dependencies installed
- [ ] FastAPI runs without errors

## ✅ Testing

### Test Path Filtering
- [ ] Python-only change does NOT trigger Vercel deployment
  ```bash
  echo "# test" >> apps/api/README.md
  git add apps/api/README.md && git commit -m "test: api" && git push
  # Check: deploy-web.yml should be SKIPPED in GitHub Actions
  ```

- [ ] Web-only change DOES trigger Vercel deployment
  ```bash
  echo "<!-- test -->" >> apps/web/app/app.vue
  git add apps/web/app/app.vue && git commit -m "test: web" && git push
  # Check: deploy-web.yml should RUN in GitHub Actions
  ```

### Test Local Development
- [ ] `pnpm dev` runs web app successfully
- [ ] `pnpm dev:api` runs FastAPI successfully
- [ ] `pnpm lint` works without errors
- [ ] `pnpm build` completes successfully

## 🎯 How to Verify Everything Works

1. **Check Vercel Dashboard:**
   - Root Directory should show `apps/web`
   - Environment variables should be set
   - Recent deployments should show correct trigger

2. **Check GitHub Actions:**
   - Go to Actions tab in your repo
   - Verify workflows run only for relevant path changes
   - Check logs for any errors

3. **Make Test Changes:**
   - Change Python file → Should NOT deploy to Vercel
   - Change Nuxt file → Should deploy to Vercel

## 🆘 Troubleshooting

### Vercel builds on Python changes
- ✅ Check Root Directory is set to `apps/web`
- ✅ Check Ignored Build Step is configured
- ✅ Verify path in git diff command

### GitHub Action doesn't run
- ✅ Check workflow path filters in `.github/workflows/deploy-web.yml`
- ✅ Verify you're pushing to correct branch (`main` or `workingdir`)
- ✅ Check GitHub Actions are enabled for your repo

### Build fails
- ✅ Check environment variables are set in both GitHub and Vercel
- ✅ Verify dependencies are installed
- ✅ Check build logs for specific error messages

---

**Once all checkboxes are complete, your monorepo is properly configured! 🎉**

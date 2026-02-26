# Vercel Configuration for Monorepo

## 🚨 Important: Vercel Dashboard Configuration Required

Since your entire repo is already connected to Vercel, you MUST update the Vercel project settings to only build from `apps/web`. Here's how:

## Option 1: Configure via Vercel Dashboard (Recommended)

### Step 1: Update Root Directory
1. Go to your Vercel project dashboard
2. Click **Settings** → **General**
3. Scroll to **Root Directory**
4. Set it to: `apps/web`
5. Click **Save**

### Step 2: Update Build Settings
1. In the same Settings page, scroll to **Build & Development Settings**
2. **Framework Preset**: Select `Nuxt.js` or `Other`
3. **Build Command**: Leave as `pnpm build` (or blank for auto-detect)
4. **Output Directory**: Leave blank (Nuxt auto-detects)
5. **Install Command**: `pnpm install --frozen-lockfile`
6. Click **Save**

### Step 3: Add Environment Variables
1. Go to **Settings** → **Environment Variables**
2. Add these variables for **Production**, **Preview**, and **Development**:
   - `NEON_DATABASE_URL`
   - `BETTER_AUTH_SECRET`
   - `BETTER_AUTH_BASE_URL`
   - `RESEND_API_KEY`
   - `RESEND_FROM_EMAIL`
   - `NODE_ENV=production`

### Step 4: Configure Ignored Build Step (Path Filtering)
1. Go to **Settings** → **Git**
2. Scroll to **Ignored Build Step**
3. Toggle it **ON**
4. Add this command:
   ```bash
   git diff --quiet HEAD^ HEAD -- apps/web/
   ```
   This tells Vercel to skip builds if only files outside `apps/web/` changed.

## Option 2: Use GitHub Actions Only (Alternative)

If you want GitHub Actions to fully control deployments:

### Step 1: Disable Vercel Auto-Deployments
1. Go to **Settings** → **Git**
2. Under **Production Branch**, uncheck **Auto-deploy**
3. Under **Preview Branches**, set to **None**
4. This prevents Vercel from auto-deploying on every push

### Step 2: Keep GitHub Action
- The GitHub Action (`.github/workflows/deploy-web.yml`) will handle all deployments
- It already has path filtering built-in
- Only runs when `apps/web/**` changes

### Step 3: Add GitHub Environment and Secrets

**Important:** Secrets are now managed in a GitHub Environment, not repository secrets.

1. Go to your GitHub repo → **Settings** → **Environments**
2. Click **New environment**
3. Name it: `production`
4. Click **Configure environment**
5. Add the following **Environment secrets**:
   - `VERCEL_TOKEN` - Get from https://vercel.com/account/tokens
   - `VERCEL_ORG_ID` - Get from Vercel project settings → General
   - `VERCEL_PROJECT_ID` - Get from Vercel project settings → General
   - `NEON_DATABASE_URL`
   - `BETTER_AUTH_SECRET`
   - `BETTER_AUTH_BASE_URL`
   - `RESEND_API_KEY`
   - `RESEND_FROM_EMAIL`

**Benefits of Environment Secrets:**
- Better organization (separate prod/staging/dev)
- Access control (who can trigger deployments)
- Optional: Require approvals before deployment
- Audit trail of all deployments

## 📋 Vercel Configuration Files

The following files help Vercel understand the monorepo:

### `vercel.json` (Root)
Already created - tells Vercel to build from `apps/web`

### How to Get Vercel IDs

```bash
# Install Vercel CLI
pnpm add -g vercel

# Link project
cd /workspaces/kali-personal-assistant
vercel link

# This will create .vercel/project.json with your IDs
cat .vercel/project.json
```

## 🧪 Testing the Setup

### Test 1: Python-only change (should NOT deploy to Vercel)
```bash
echo "# Test change" >> apps/api/README.md
git add apps/api/README.md
git commit -m "test: api change only"
git push
# Check GitHub Actions - deploy-web.yml should be skipped
```

### Test 2: Web-only change (should deploy to Vercel)
```bash
echo "<!-- Test -->" >> apps/web/app.vue
git add apps/web/app.vue
git commit -m "test: web change"
git push
# Check GitHub Actions - deploy-web.yml should run
```

## ✅ Recommended Setup

**Use BOTH approaches:**
1. Configure Vercel's Root Directory to `apps/web` (prevents accidental builds)
2. Keep GitHub Action with path filtering (for explicit control)
3. Use GitHub Action secrets for environment variables

This gives you:
- ✅ Vercel UI deployments work correctly from `apps/web`
- ✅ GitHub Actions control when deployments happen
- ✅ Python changes never trigger builds
- ✅ Preview deployments work for web changes only

## 🚫 What NOT to Do

❌ Don't leave Vercel Root Directory as `.` (root)
❌ Don't skip the "Ignored Build Step" configuration
❌ Don't forget to set environment variables in both GitHub and Vercel

## 📞 Need Help?

If builds still trigger for Python changes:
1. Check Vercel deployment logs to see what triggered the build
2. Verify Root Directory is set to `apps/web`
3. Verify "Ignored Build Step" command is active
4. Check GitHub Actions logs to see if workflow was skipped

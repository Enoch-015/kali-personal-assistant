# GitHub Environments Setup Guide

This guide explains how to set up GitHub Environments for your deployment workflows.

## 🌍 What are GitHub Environments?

GitHub Environments allow you to:
- Organize secrets per environment (production, staging, development)
- Control who can deploy to each environment
- Require manual approval before deployment (optional)
- Track deployment history and audit trails
- Set environment-specific variables

## 📋 Step-by-Step Setup

### 1. Create the Production Environment

1. Go to your GitHub repository
2. Click **Settings** (top menu)
3. In the left sidebar, click **Environments**
4. Click **New environment** button
5. Enter name: `production`
6. Click **Configure environment**

### 2. Add Environment Secrets

On the environment configuration page, scroll to **Environment secrets** section:

Click **Add secret** for each of the following:

#### Vercel Configuration
```
Name: VERCEL_TOKEN
Value: [Get from https://vercel.com/account/tokens]

Name: VERCEL_ORG_ID
Value: [Get from Vercel Project Settings → General]

Name: VERCEL_PROJECT_ID
Value: [Get from Vercel Project Settings → General]
```

#### Database Configuration
```
Name: TURSO_DATABASE_URL
Value: [Your Turso database URL]

Name: TURSO_AUTH_TOKEN
Value: [Your Turso auth token]
```

#### Authentication
```
Name: BETTER_AUTH_SECRET
Value: [Your Better Auth secret key]

Name: BETTER_AUTH_BASE_URL
Value: [Your production URL, e.g., https://your-app.vercel.app]
```

#### Email Service
```
Name: RESEND_API_KEY
Value: [Your Resend API key]

Name: RESEND_FROM_EMAIL
Value: [Your sender email, e.g., Your App <onboarding@resend.dev>]
```

### 3. Optional: Configure Protection Rules

In the same environment configuration page, you can add:

#### Deployment Branches
- Specify which branches can deploy to this environment
- Example: Only allow `main` branch

#### Required Reviewers
- Require manual approval before deployment
- Select team members who can approve

#### Wait Timer
- Add a delay before deployment starts
- Useful for last-minute checks

### 4. Verify Configuration

1. Go back to **Environments** page
2. You should see `production` listed
3. Click on it to verify all secrets are added
4. Check that 9 secrets are configured

## 🔄 How Workflows Use Environments

Your GitHub Actions workflows reference the environment:

```yaml
jobs:
  deploy:
    name: Deploy to Vercel
    runs-on: ubuntu-latest
    environment: production  # ← This line
    steps:
      # ... deployment steps
```

When the workflow runs:
1. It requests access to the `production` environment
2. GitHub checks protection rules (if any)
3. Secrets from the environment become available
4. Deployment proceeds

## 🎯 Adding More Environments

You can create additional environments for different stages:

### Staging Environment
```
Name: staging
Secrets: Same as production but with staging URLs
Protection: Less strict, auto-deploy on push
```

### Development Environment
```
Name: development
Secrets: Development database and services
Protection: None, anyone can deploy
```

Then update your workflow to use different environments:

```yaml
on:
  push:
    branches:
      - main           # Use production environment
      - develop        # Use development environment

jobs:
  deploy:
    environment: ${{ github.ref == 'refs/heads/main' && 'production' || 'development' }}
```

## 📊 Benefits You Get

✅ **Security**: Secrets are scoped to environments, not global
✅ **Organization**: Clear separation between prod/staging/dev
✅ **Audit Trail**: See who deployed what and when
✅ **Access Control**: Limit who can trigger production deployments
✅ **Flexibility**: Different secrets for different environments

## 🔍 Viewing Deployment History

1. Go to your repository
2. Click **Actions** tab
3. Click on any workflow run
4. You'll see which environment was used
5. Click on the job to see environment details

Or go to **Environments** → **production** → **Deployments** to see history.

## 🆘 Troubleshooting

### "Environment not found" error
- ✅ Ensure environment name is exactly `production` (lowercase)
- ✅ Check that environment exists in Settings → Environments

### "Secret not found" error
- ✅ Verify secret name matches exactly (case-sensitive)
- ✅ Ensure secret is added to the environment, not repository secrets
- ✅ Check workflow specifies correct environment

### Workflow waiting for approval
- ✅ You may have set up required reviewers
- ✅ Go to Actions tab and approve the deployment
- ✅ Or remove required reviewers if not needed

## 📖 Learn More

- [GitHub Environments Documentation](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Environment Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Deployment Protection Rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment#deployment-protection-rules)

---

**Once your `production` environment is set up with all secrets, your deployments will work automatically! 🚀**

# VS Code Monorepo Configuration Guide

## 🔧 TypeScript Configuration

Your monorepo now has a proper TypeScript setup:

### Structure
```
/                                  # Root workspace
├── tsconfig.json                  # Project references (points to apps/web)
├── .vscode/settings.json          # Global workspace settings
└── apps/
    └── web/
        ├── tsconfig.json          # Nuxt TypeScript config
        └── .vscode/settings.json  # Web-specific settings
```

## 🚨 Fix TypeScript Errors in VS Code

If you're seeing errors like:
- `Cannot find module 'drizzle-orm/libsql'`
- `Cannot find module './lib/env'`
- `Cannot read file '/workspaces/kali-personal-assistant/tsconfig.json'`

**Solution: Reload VS Code TypeScript Server**

### Option 1: Command Palette (Recommended)
1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type: `TypeScript: Restart TS Server`
3. Press Enter

### Option 2: Reload VS Code Window
1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type: `Developer: Reload Window`
3. Press Enter

### Option 3: Use the Workspace File
1. Close VS Code
2. Open the workspace file:
   ```bash
   code kali-personal-assistant.code-workspace
   ```
3. This opens VS Code with proper multi-root workspace support

## 📂 Workspace Setup

### Multi-Root Workspace (Recommended)
Open the workspace file for better organization:
```bash
code kali-personal-assistant.code-workspace
```

This gives you:
- ✅ Separate folder views for Root, Web, and API
- ✅ Proper TypeScript resolution
- ✅ Better ESLint integration
- ✅ Organized file explorer

### Single-Root Workspace (Current)
If you prefer opening just the root folder:
```bash
code .
```

Make sure to:
- Reload TypeScript server after opening
- Ensure `.vscode/settings.json` exists at root
- TypeScript SDK is pointed to `apps/web/node_modules/typescript/lib`

## 🔍 Verifying Everything Works

### 1. Check TypeScript SDK
1. Open any `.ts` file in `apps/web/`
2. Bottom right of VS Code should show TypeScript version
3. Click on version number → should say "Using workspace TypeScript"

### 2. Check ESLint
1. Open a `.vue` or `.ts` file in `apps/web/`
2. ESLint should show warnings/errors if any exist
3. Save file → should auto-format via ESLint

### 3. Check Python (for API)
1. Open `apps/api/src/main.py`
2. Python interpreter should be set to `apps/api/venv`
3. Imports should resolve correctly

## 🛠️ Settings Explained

### Root `.vscode/settings.json`
- `typescript.tsdk`: Points to TypeScript in web app
- `eslint.workingDirectories`: ESLint runs from web app directory
- File exclusions: Hides build artifacts and dependencies

### `apps/web/.vscode/settings.json`
- ESLint auto-fix on save
- Prettier disabled (using ESLint for formatting)
- Custom ESLint rule customizations

### `tsconfig.json` (Root)
- Project references setup
- Points to `apps/web` as the TypeScript project
- Helps VS Code understand monorepo structure

### `apps/web/tsconfig.json`
- Nuxt-specific TypeScript config
- Path aliases (`@/` and `~/`)
- Composite project for better builds

## 🐛 Troubleshooting

### "Cannot find module 'drizzle-kit'"
**Cause:** TypeScript can't find the package
**Fix:** 
```bash
cd apps/web
pnpm install
# Then reload TypeScript server in VS Code
```

### ESLint not working
**Cause:** ESLint working directory not set correctly
**Fix:** Check `.vscode/settings.json` has correct `eslint.workingDirectories`

### Python imports not resolving
**Cause:** Wrong Python interpreter
**Fix:**
1. `Ctrl+Shift+P` → `Python: Select Interpreter`
2. Choose `apps/api/venv/bin/python`

### TypeScript shows errors for correct code
**Cause:** TS server using wrong tsconfig
**Fix:** Restart TS server (see above)

## ✅ Quick Setup Checklist

After cloning or restructuring:
- [ ] Run `pnpm install` at root
- [ ] Run `cd apps/api && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- [ ] Open VS Code: `code kali-personal-assistant.code-workspace`
- [ ] Reload TypeScript server
- [ ] Verify TypeScript SDK is "Using workspace version"
- [ ] Test ESLint auto-fix by saving a file in `apps/web/`

---

**With these settings, TypeScript, ESLint, and Python should all work correctly in your monorepo! 🎉**

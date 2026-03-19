---
description: Build and release from dev branch to main branch
---

# Release Workflow: dev → main

## Prerequisites

- **dev branch**: Source code only, `static/` is in `.gitignore`
- **main branch**: Source code + compiled `static/` directory (for deployment)
- Build artifacts are NOT tracked on dev to avoid merge conflicts

## Steps

### 1. Ensure dev branch is ready

```bash
git checkout dev
git status  # make sure working tree is clean
```

### 2. Build frontend assets

```bash
cd webui
npm run build   # outputs to ../static/
cd ..
```

// turbo
### 3. Switch to main and merge dev

```bash
git checkout main
git merge dev -m "merge: dev → main"
```

### 4. Remove `static/` from .gitignore (if merged from dev)

```bash
# Check if .gitignore contains static/ (merged from dev)
grep -n "^static/" .gitignore && sed -i '' '/^static\/$/d' .gitignore
```

### 5. Commit build artifacts

```bash
git add static/ .gitignore
git commit -m "build: update static assets"
```

### 6. Push to remote

```bash
git push origin main
```

// turbo
### 7. Switch back to dev

```bash
git checkout dev
```

## First-Time Setup (one-time only)

If dev branch is still tracking `static/`, clean it up first:

```bash
git checkout dev

# Remove static/ from git tracking (keep local files)
git rm -r --cached static/

# Add static/ to dev's .gitignore
echo "static/" >> .gitignore

git add .gitignore
git commit -m "chore: stop tracking static/ on dev branch"
```

> ⚠️ **Note**: main branch's `.gitignore` must NOT exclude `static/`, since main needs to track it for deployment. After merging dev → main, always verify and remove the `static/` line from main's `.gitignore` if present (Step 4).

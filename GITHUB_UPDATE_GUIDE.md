# How to Push These Changes to GitHub

This guide will walk you through updating your GitHub repository with the security fixes and improvements.

## What Was Changed

1. **README.md** - Added security warnings, verification steps, and best practices
2. **.gitignore** - Added protection against accidentally committing sensitive context files
3. **examples/README.md** - New file explaining that examples are sanitized
4. **setup.py** - Added Windows PowerShell hook support

## Step-by-Step Instructions

### 1. Check What Changed

First, let's see what files were modified:

```powershell
cd c:\Users\dross\Project\claude-persistent-context
git status
```

You should see:
- Modified: README.md
- Modified: .gitignore
- Modified: setup.py
- Untracked: examples/README.md
- Untracked: GITHUB_UPDATE_GUIDE.md (this file)

### 2. Review the Changes

Look at what changed in each file:

```powershell
git diff README.md
git diff .gitignore
git diff setup.py
```

### 3. Stage the Changes

Add all the changed files to git:

```powershell
git add README.md
git add .gitignore
git add setup.py
git add examples/README.md
git add GITHUB_UPDATE_GUIDE.md
```

Or add everything at once:

```powershell
git add .
```

### 4. Commit the Changes

Create a commit with a descriptive message:

```powershell
git commit -m "Add security warnings and improve documentation

- Add prominent security warning about sensitive data
- Add .gitignore rules to prevent committing context files
- Add verification steps for installation
- Add security best practices section
- Add Windows PowerShell hook support
- Add README to examples directory explaining sanitization"
```

### 5. Push to GitHub

Push your changes to the main branch:

```powershell
git push origin main
```

If this is your first push from this machine, you may need to authenticate with GitHub.

## If You Need to Set Up Git Credentials

If you haven't set up git on this machine yet:

### Option 1: GitHub CLI (Recommended)

```powershell
# Install GitHub CLI if not already installed
winget install GitHub.cli

# Authenticate
gh auth login
```

Follow the prompts to authenticate via browser.

### Option 2: Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name like "Windows Laptop"
4. Select scopes: `repo` (full control of private repositories)
5. Click "Generate token"
6. Copy the token (you won't see it again!)

Then when you push:

```powershell
git push origin main
```

When prompted for username: enter your GitHub username
When prompted for password: paste the personal access token

### Option 3: SSH Key

If you prefer SSH:

```powershell
# Generate SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy the public key
Get-Content ~/.ssh/id_ed25519.pub | clip

# Add to GitHub: https://github.com/settings/keys
# Click "New SSH key", paste, and save

# Update remote URL to use SSH
git remote set-url origin git@github.com:dross50/claude-persistent-context.git

# Push
git push origin main
```

## Verify on GitHub

After pushing, visit:
https://github.com/dross50/claude-persistent-context

You should see:
- The security warning at the top of the README
- Updated files with your commit message
- The new examples/README.md file

## Troubleshooting

### "Permission denied"
- You need to authenticate (see credential setup above)

### "Updates were rejected"
- Someone else pushed changes, or you made changes on another machine
- Run: `git pull origin main` then `git push origin main`

### "Nothing to commit"
- Changes weren't staged
- Run: `git add .` then commit again

## Next Steps

After successfully pushing:
1. Delete this guide if you want: `git rm GITHUB_UPDATE_GUIDE.md && git commit -m "Remove update guide" && git push`
2. Or keep it for future reference
3. Your repository is now secure and properly documented!


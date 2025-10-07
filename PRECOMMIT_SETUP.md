# Pre-Commit Hooks Setup

Pre-commit hooks automatically check your code **before** you commit, catching issues early.

## Quick Setup (Windows)

```powershell
# Run the setup script
.\scripts\setup_precommit.ps1
```

## Quick Setup (Linux/Mac)

```bash
# Run the setup script
bash scripts/setup_precommit.sh
```

## Manual Setup

```bash
# 1. Install pre-commit
pip install pre-commit

# 2. Install the git hooks
pre-commit install

# 3. (Optional) Run on all files to verify
pre-commit run --all-files
```

## What Gets Checked

Every time you run `git commit`, these checks run automatically:

1. **Ruff** - Fast Python linter (auto-fixes issues)
2. **Black** - Code formatter (auto-formats)
3. **MyPy** - Type checker (strict mode)
4. **Detect-secrets** - Prevents committing secrets/keys

## How It Works

```bash
# When you commit:
git add myfile.py
git commit -m "my changes"

# Pre-commit runs automatically:
# ✓ Ruff: checking and fixing...
# ✓ Black: formatting...
# ✓ MyPy: type checking...
# ✓ Detect-secrets: scanning...

# If all pass: commit succeeds ✅
# If any fail: commit blocked ❌ (fix issues and try again)
```

## Running Manually

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Run specific hook
pre-commit run ruff
pre-commit run black
pre-commit run mypy
```

## Skipping Hooks (Emergency Only)

```bash
# Skip hooks for one commit (NOT RECOMMENDED)
git commit --no-verify -m "emergency fix"
```

## Updating Hooks

```bash
# Update to latest versions
pre-commit autoupdate

# Then commit the updated .pre-commit-config.yaml
git add .pre-commit-config.yaml
git commit -m "chore: update pre-commit hooks"
```

## Troubleshooting

### "pre-commit: command not found"

```bash
# Install pre-commit
pip install pre-commit

# Or with pipx (recommended)
pipx install pre-commit
```

### Hooks are slow

```bash
# Skip mypy for faster commits (check in CI instead)
SKIP=mypy git commit -m "quick fix"
```

### MyPy errors on dependencies

The `.pre-commit-config.yaml` is configured to only check `cns_py/` and ignore missing imports:

```yaml
- id: mypy
  args: ["--strict", "cns_py"]
```

## Benefits

✅ **Catch issues early** - Before CI, before review  
✅ **Consistent style** - Black formats everything  
✅ **Type safety** - MyPy catches type errors  
✅ **Security** - Detect-secrets prevents leaks  
✅ **Fast feedback** - Seconds, not minutes (vs CI)  

## CI vs Pre-Commit

| Check | Pre-Commit | CI |
|-------|------------|-----|
| **When** | Before commit | After push |
| **Speed** | Seconds | Minutes |
| **Scope** | Changed files | All files |
| **Blocking** | Local only | Blocks merge |

**Best practice:** Use both! Pre-commit for fast feedback, CI for comprehensive checks.

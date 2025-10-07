# VS Code Configuration

This directory contains VS Code workspace settings for the CNS project.

## Auto-Activation of Virtual Environment

The `.venv` will automatically activate when you:

1. **Open the workspace** - VS Code will detect and use `.venv/Scripts/python.exe`
2. **Open a new terminal** - The venv will auto-activate
3. **Run Python files** - Will use the venv Python interpreter

## Settings Configured

### Python Environment
- **Interpreter**: `.venv/Scripts/python.exe`
- **Auto-activate**: Enabled for all terminals

### Testing
- **Framework**: pytest
- **Test directory**: `tests/`

### Linting & Formatting
- **Linter**: Ruff (enabled)
- **Formatter**: Black
- **Format on save**: Enabled
- **Organize imports on save**: Enabled

### File Exclusions
Hidden from explorer:
- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`

## Manual Activation (if needed)

If the venv doesn't auto-activate, you can manually activate it:

### PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
```

### Command Prompt
```cmd
.venv\Scripts\activate.bat
```

### Git Bash / WSL
```bash
source .venv/Scripts/activate
```

## Verifying Activation

Check if venv is active:
```powershell
# Should show path to .venv
python -c "import sys; print(sys.executable)"

# Should show (.venv) prefix in prompt
# (.venv) PS C:\...\cns>
```

## Troubleshooting

### Venv doesn't activate automatically
1. Reload VS Code window: `Ctrl+Shift+P` → "Developer: Reload Window"
2. Check Python extension is installed
3. Verify `.venv` exists: `Test-Path .venv` should return `True`

### "Running scripts is disabled" error
Run this in PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Wrong Python interpreter selected
1. `Ctrl+Shift+P` → "Python: Select Interpreter"
2. Choose `.venv/Scripts/python.exe`

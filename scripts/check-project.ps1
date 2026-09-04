$ErrorActionPreference = "Stop"

$BackendPython = Join-Path $PSScriptRoot "..\.venv-backend\Scripts\python.exe"
if (Test-Path $BackendPython) {
  Push-Location (Join-Path $PSScriptRoot "..\backend")
  & $BackendPython -m pytest -o cache_dir=C:\Nexus\.pytest-cache-backend
  & $BackendPython -m ruff check . --no-cache
  Pop-Location
} else {
  Write-Warning "Backend virtual environment not found at $BackendPython"
}

Push-Location frontend
npm.cmd install
npm.cmd run build
Pop-Location

Write-Host "Project checks completed."

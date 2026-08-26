# Setup Runbook

This runbook documents the current Nexus local development flow from an empty checkout to a running backend and frontend.

## 1. Confirm Tooling

Check Node:

```powershell
node -v
npm.cmd -v
```

Check Python by absolute path:

```powershell
& "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe" --version
```

The current machine has Python 3.14.7 installed at:

```text
C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe
```

To make `python` work globally, add these folders to PATH:

```text
C:\Users\user\AppData\Local\Python\pythoncore-3.14-64
C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Scripts
```

Disable Windows Store Python aliases if they interfere:

```text
Settings -> Apps -> Advanced app settings -> App execution aliases
```

Turn off `python.exe` and `python3.exe`.

## 2. Configure Environment

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Fill these values before using real integrations:

```text
TELEGRAM_BOT_TOKEN=
CHAPA_SECRET_KEY=
CHAPA_WEBHOOK_SECRET=
CHAPA_CALLBACK_URL=
```

Keep local defaults for development unless your Docker ports differ:

```text
DATABASE_URL=postgresql+asyncpg://nexus:nexus@localhost:5432/nexus
REDIS_URL=redis://localhost:6379/0
```

## 3. Start Infrastructure

Start PostgreSQL and Redis:

```powershell
docker compose -f infra/docker-compose.yml up -d
```

Check containers:

```powershell
docker compose -f infra/docker-compose.yml ps
```

## 4. Install Backend

Create the backend virtual environment at the project root. This workspace blocks some nested generated folders, so root-level `.venv-backend` is the reliable path.

```powershell
cd C:\Nexus
& "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m venv .venv-backend
& ".\.venv-backend\Scripts\python.exe" -m pip install -e ".\backend[dev]"
```

Run database migrations:

```powershell
cd C:\Nexus\backend
& "..\.venv-backend\Scripts\python.exe" -m alembic upgrade head
```

Start the API:

```powershell
& "..\.venv-backend\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Useful URLs:

```text
http://localhost:8000/v1/health
http://localhost:8000/v1/health/ready
http://localhost:8000/docs
```

`/v1/health` only confirms the API process is alive. `/v1/health/ready` checks PostgreSQL and Redis.

## 5. Install Frontend

```powershell
cd C:\Nexus\frontend
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://localhost:5173
```

The Vite config lives at the repository root in `vite.frontend.config.mjs` so cache and build output can go to workspace-writable root paths.

## 6. Run Checks

Run the full local check script:

```powershell
cd C:\Nexus
powershell -ExecutionPolicy Bypass -File scripts\check-project.ps1
```

What it runs:

```text
backend pytest
backend ruff
frontend npm install
frontend build
```

Run backend checks manually:

```powershell
cd C:\Nexus\backend
& "..\.venv-backend\Scripts\python.exe" -m pytest -o cache_dir=C:\Nexus\.pytest-cache-backend
& "..\.venv-backend\Scripts\python.exe" -m ruff check . --no-cache
```

Run frontend checks manually:

```powershell
cd C:\Nexus\frontend
npm.cmd run build
npm.cmd audit --json
```


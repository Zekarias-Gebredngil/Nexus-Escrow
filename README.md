# Nexus

Nexus is a Telegram micro-escrow platform foundation for Ethiopia. The project follows the uploaded architecture: zero-balance orchestration, Chapa-managed custody, PostgreSQL-backed escrow state, Redis/Celery background work, Telegram bot entry points, and a Telegram Web App frontend.

## Structure

- `backend/`: FastAPI service, SQLAlchemy models, Alembic migrations, Chapa and Telegram integrations, Celery worker.
- `frontend/`: React + Vite Telegram Web App shell.
- `infra/`: Docker Compose for local PostgreSQL and Redis.
- `docs/`: implementation notes derived from the architecture documents.

## Documentation

- [docs/setup-runbook.md](docs/setup-runbook.md): step-by-step local setup and daily commands.
- [docs/api-workflows.md](docs/api-workflows.md): current API endpoints and escrow workflow order.
- [docs/testing-strategy.md](docs/testing-strategy.md): test layers and end-to-end confirmation plan.
- [docs/deployment.md](docs/deployment.md): staging/production deployment and rollback checklist.
- [docs/implementation-log.md](docs/implementation-log.md): implementation steps completed so far.
- [docs/architecture-decisions.md](docs/architecture-decisions.md): architecture rules carried from the spec.

## Local Start

1. Copy `.env.example` to `.env` and fill secrets.
2. Start infrastructure:

```powershell
docker compose -f infra/docker-compose.yml up -d
```

3. Backend:

```powershell
cd C:\Nexus
& "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m venv .venv-backend
& ".\.venv-backend\Scripts\python.exe" -m pip install -e ".\backend[dev]"
cd backend
& "..\.venv-backend\Scripts\python.exe" -m alembic upgrade head
& "..\.venv-backend\Scripts\python.exe" -m uvicorn app.main:app --reload
```

4. Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

5. Run all available checks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check-project.ps1
```

## Design Principles

- No user balances are stored or represented as spendable value.
- Escrow state transitions are explicit and audited.
- Payment confirmation only moves state after Chapa webhook signature verification.
- Financial math is centralized and uses decimal arithmetic.
- External side effects live behind service boundaries for testing and replacement.

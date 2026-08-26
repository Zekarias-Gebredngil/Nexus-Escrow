# Deployment Guide

This guide describes how to deploy Nexus safely to staging and production.

## Deployment Targets

Nexus has four runtime components:

- Backend API: FastAPI served by Uvicorn or Gunicorn/Uvicorn workers.
- Worker: Celery worker connected to Redis.
- Database: PostgreSQL 15 or newer.
- Frontend: Static Vite build served by a web server or object storage/CDN.

Redis is required for:

- Celery broker.
- Celery result backend.
- Future rate limiting and coarse distributed locks.

## Recommended Production Shape

Use managed services where possible:

- PostgreSQL: managed Postgres with automated backups and point-in-time recovery.
- Redis: managed Redis with persistence or acceptable task-loss policy.
- Backend: container service or VM behind HTTPS reverse proxy.
- Worker: separate container or process from the API.
- Frontend: static hosting behind HTTPS.
- Secrets: environment variables from the platform secret manager.

Do not run API and worker as the same process in production. They scale and fail differently.

## Required Environment Variables

Backend:

```text
APP_ENV=production
API_BASE_URL=https://api.example.com
FRONTEND_BASE_URL=https://app.example.com
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
SECRET_KEY=...
TELEGRAM_BOT_TOKEN=...
CHAPA_SECRET_KEY=...
CHAPA_BASE_URL=https://api.chapa.co
CHAPA_WEBHOOK_SECRET=...
CHAPA_CALLBACK_URL=https://api.example.com/v1/webhooks/chapa
PLATFORM_FEE_RATE=0.025
GATEWAY_FEE_RATE=0.020
ADMIN_NET_SHARE_RATE=0.40
AUTO_RELEASE_HOURS=48
```

Frontend:

```text
VITE_API_BASE_URL=https://api.example.com
```

Secrets must not be committed to git, Docker images, frontend bundles, or docs.

## Pre-Deployment Checklist

Before deploying a build:

- Confirm `APP_ENV` is correct.
- Confirm Chapa keys are sandbox keys for staging and production keys only for production.
- Confirm Telegram bot token belongs to the intended bot.
- Confirm callback URLs use HTTPS.
- Confirm database backups are enabled.
- Confirm Redis is reachable from API and worker.
- Confirm migrations have been reviewed.
- Confirm `.env` files are not copied into images.

Run checks:

```powershell
cd C:\Nexus
powershell -ExecutionPolicy Bypass -File scripts\check-project.ps1
```

Expected:

```text
backend pytest passes
backend ruff passes
frontend build succeeds
```

## Build

Build backend container:

```powershell
docker build -t nexus-backend:latest .\backend
```

Build frontend container:

```powershell
docker build -t nexus-frontend:latest .\frontend
```

Or build the frontend static bundle:

```powershell
cd C:\Nexus\frontend
npm.cmd ci
npm.cmd run build
```

Static output is written to:

```text
C:\Nexus\dist\frontend
```

## Database Migration

Apply migrations before shifting traffic to the new API version:

```powershell
cd C:\Nexus\backend
& "..\.venv-backend\Scripts\python.exe" -m alembic upgrade head
```

Production migration rule:

- Take a database backup first.
- Run migrations once, from a release job or admin shell.
- Do not let every API replica run migrations on startup.

## Start Commands

API process:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Linux production option:

```bash
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 60
```

Worker process:

```powershell
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

For Windows local development, use:

```powershell
& "C:\Nexus\.venv-backend\Scripts\celery.exe" -A app.workers.celery_app.celery_app worker --loglevel=info
```

## Health Checks

Use liveness for simple process checks:

```http
GET /v1/health
```

Use readiness for dependency checks:

```http
GET /v1/health/ready
```

Production load balancers should use `/v1/health` for cheap liveness. Deployment systems should use `/v1/health/ready` before promoting a release.

## Staging Deployment

Staging must use:

- Chapa sandbox credentials.
- Telegram test bot.
- Separate PostgreSQL database.
- Separate Redis instance or namespace.
- Non-production callback URLs.

Staging verification:

1. Deploy API.
2. Run Alembic migrations.
3. Deploy worker.
4. Deploy frontend.
5. Confirm `/v1/health`.
6. Confirm `/v1/health/ready`.
7. Open `/docs`.
8. Run local E2E workflow from [testing-strategy.md](testing-strategy.md).
9. Send a real Chapa sandbox webhook or signed test webhook.
10. Confirm Celery receives auto-release task after shipping.

Promote to production only after staging E2E passes.

## Production Deployment

Production rollout:

1. Create release tag or immutable build.
2. Back up database.
3. Deploy new API image with zero or low traffic.
4. Run migrations.
5. Start worker image.
6. Check `/v1/health/ready`.
7. Shift traffic to new API.
8. Deploy frontend static bundle.
9. Confirm Telegram Web App opens.
10. Confirm Chapa webhook endpoint receives signed test event.
11. Monitor logs and metrics for at least one escrow cycle.

## End-to-End Production Confirmation

Use the smallest safe transaction supported by Chapa and business policy.

Confirm:

- Buyer opens Telegram Web App.
- Phone identity is captured.
- Escrow is created.
- Chapa checkout initializes.
- Chapa redirects or calls back successfully.
- Signed webhook moves escrow to `PAID`.
- Seller receives paid notification once implemented.
- Seller submits tracking.
- Buyer confirms receipt or admin resolves dispute.
- Terminal state is `RELEASED` or `REFUNDED`.
- Audit log contains each transition.
- No internal user balance row or wallet balance exists.

For real money tests, record:

- Escrow ID.
- Chapa transaction reference.
- Buyer Telegram ID.
- Seller Telegram ID.
- Channel ID.
- Final escrow state.
- Chapa dashboard settlement result.

## Monitoring

Minimum production signals:

- API error rate.
- API latency.
- `/v1/health/ready` failures.
- Database connection pool exhaustion.
- Redis connection failures.
- Celery queue depth.
- Celery task failures and retries.
- Chapa webhook count by status.
- Invalid webhook signature count.
- Escrows stuck in `WAITING_FOR_PAYMENT`.
- Escrows stuck in `SHIPPED` past `auto_release_at`.
- Escrows stuck in `DISPUTED`.

## Rollback

Rollback API:

1. Stop traffic to the new API version.
2. Route traffic back to the previous API version.
3. Keep workers compatible with current database schema.
4. Inspect failed webhooks and queued tasks before replaying.

Rollback frontend:

1. Re-publish previous static bundle.
2. Purge CDN cache if used.
3. Confirm Telegram Web App opens the previous bundle.

Rollback database:

- Prefer forward-fix migrations.
- Use database restore only for severe cases.
- Never restore production database casually after real payment webhooks have been processed.

Payment-specific rollback rule:

- Do not replay Chapa webhooks manually unless the escrow state and audit log have been inspected.
- Do not move terminal `RELEASED` or `REFUNDED` escrows backward.

## Security Deployment Notes

- Serve API and frontend only over HTTPS in staging and production.
- Restrict CORS to the real frontend origin.
- Rotate `CHAPA_WEBHOOK_SECRET` if a secret leaks.
- Keep Telegram bot token in secret manager only.
- Log webhook metadata, not full sensitive payloads.
- Alert on invalid webhook signatures.
- Rate limit public endpoints before launch.

## Release Sign-Off

A release is ready when:

- Automated checks pass.
- Migration plan is reviewed.
- Staging E2E passes.
- Rollback plan is written.
- Chapa sandbox or production verification is complete.
- Telegram Web App opens from the intended bot.
- Logs show no startup errors in API or worker.


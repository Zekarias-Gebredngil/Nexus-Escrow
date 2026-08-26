# Testing Strategy

This strategy defines how Nexus should be tested before local development changes, staging release, and production deployment.

## Goals

Testing must prove four things:

- The escrow state machine rejects invalid transitions.
- Financial calculations are deterministic and auditable.
- Chapa and Telegram inputs are verified before state changes.
- A buyer, seller, admin, webhook, and worker can complete the escrow lifecycle end to end.

The platform must never treat database rows as user wallet balances. Tests should confirm workflow state and payout instructions, not internal custody.

## Test Layers

## 1. Static Checks

Purpose: catch simple correctness and maintainability issues before runtime.

Run:

```powershell
cd C:\Nexus\backend
& "..\.venv-backend\Scripts\python.exe" -m ruff check . --no-cache
```

Pass criteria:

- No Ruff errors.
- No unused imports.
- No FastAPI dependency-default warnings.
- No accidental broad exception handling around payment state changes.

## 2. Unit Tests

Purpose: verify pure business logic without PostgreSQL, Redis, Chapa, or Telegram.

Current examples:

```powershell
cd C:\Nexus\backend
& "..\.venv-backend\Scripts\python.exe" -m pytest tests\test_fees.py tests\test_state_machine.py -o cache_dir=C:\Nexus\.pytest-cache-backend
```

Required coverage:

- Fee calculation for normal prices.
- Fee rounding at decimal boundaries.
- State machine happy path.
- State machine dispute path.
- Terminal states remain terminal.
- Invalid transitions are rejected.

Pass criteria:

- All tests pass.
- Fee results match documented formulas.
- No state transition bypasses `EscrowService._transition()`.

## 3. API Contract Tests

Purpose: confirm the exposed API remains stable.

Run:

```powershell
cd C:\Nexus\backend
& "..\.venv-backend\Scripts\python.exe" -m pytest tests\test_app_contract.py -o cache_dir=C:\Nexus\.pytest-cache-backend
```

Pass criteria:

- OpenAPI exposes expected `/v1` paths.
- Root and docs behavior remain intentional.
- New endpoints are added to the contract test when created.

## 4. Database Integration Tests

Purpose: prove real persistence behavior, row locking, audit logs, constraints, and migrations.

These tests should be added next. They require PostgreSQL.

Start infrastructure:

```powershell
docker compose -f infra/docker-compose.yml up -d
```

Run migrations:

```powershell
cd C:\Nexus\backend
& "..\.venv-backend\Scripts\python.exe" -m alembic upgrade head
```

Minimum integration cases:

- Creating an escrow writes one `escrows` row.
- Confirming terms writes an audit log row.
- Chapa webhook changes only `WAITING_FOR_PAYMENT -> PAID`.
- Duplicate Chapa webhook is idempotent and does not add a second payment transition.
- Concurrent release/refund attempts cannot both win.
- Channel admin mismatch cannot resolve a dispute.

Pass criteria:

- Migrations apply from an empty database.
- Constraints reject invalid foreign keys.
- State changes and audit logs commit atomically.
- Race-condition tests show one valid terminal outcome.

## 5. Webhook Verification Tests

Purpose: prove Chapa webhook security.

Required cases:

- Missing signature returns `401`.
- Invalid signature returns `403`.
- Valid signature with unknown `tx_ref` returns received but does not mutate state.
- Valid signature with successful status moves escrow to `PAID`.
- Valid signature with non-success status does not move escrow to `PAID`.

Manual signature generation example:

```powershell
$secret = "local-webhook-secret"
$body = '{"tx_ref":"nexus-example","status":"success"}'
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($secret)
$hashBytes = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($body))
$signature = [BitConverter]::ToString($hashBytes).Replace("-", "").ToLower()
$signature
```

Pass criteria:

- Only valid HMAC signatures are accepted.
- State does not change before signature verification.

## 6. Worker Tests

Purpose: prove asynchronous timeout behavior.

Required cases:

- Shipping schedules `tasks.process_auto_release`.
- Auto-release exits if escrow is not `SHIPPED`.
- Auto-release moves `SHIPPED -> RELEASED`.
- Auto-release does not override `DISPUTED`.
- Auto-release does not override already `RELEASED` or `REFUNDED`.

Pass criteria:

- Celery task is safe to retry.
- Worker behavior is defensive and state-aware.

## 7. Frontend Tests

Purpose: prove the Telegram Web App shell builds and handles user-facing states.

Run:

```powershell
cd C:\Nexus\frontend
npm.cmd run build
npm.cmd audit --json
```

Pass criteria:

- TypeScript passes.
- Production bundle builds.
- npm audit reports zero vulnerabilities.
- UI does not depend on unavailable backend data at startup.

Recommended next frontend tests:

- Render escrow status from API data.
- Show loading, error, empty, and success states.
- Disable invalid action buttons for current escrow state.
- Verify mobile viewport layout.

## 8. End-to-End Tests

Purpose: prove the whole product flow works with real services or controlled test doubles.

E2E should run against:

- FastAPI backend
- PostgreSQL
- Redis
- Celery worker
- Frontend dev or preview server
- Chapa sandbox or mocked Chapa webhook
- Telegram test bot or mocked TWA init data

## Local E2E Confirmation

Start infrastructure:

```powershell
cd C:\Nexus
docker compose -f infra/docker-compose.yml up -d
```

Run migrations:

```powershell
cd C:\Nexus\backend
& "..\.venv-backend\Scripts\python.exe" -m alembic upgrade head
```

Start backend:

```powershell
& "..\.venv-backend\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Start worker in a second shell:

```powershell
cd C:\Nexus\backend
& "..\.venv-backend\Scripts\celery.exe" -A app.workers.celery_app.celery_app worker --loglevel=info
```

Start frontend in a third shell:

```powershell
cd C:\Nexus\frontend
npm.cmd run dev
```

Confirm health:

```powershell
Invoke-RestMethod http://localhost:8000/v1/health
Invoke-RestMethod http://localhost:8000/v1/health/ready
```

Create buyer:

```powershell
Invoke-RestMethod -Method Put -Uri http://localhost:8000/v1/users/1001 -ContentType "application/json" -Body '{
  "id": 1001,
  "username": "buyer",
  "first_name": "Buyer",
  "phone_number": "+251900000001"
}'
```

Create seller:

```powershell
Invoke-RestMethod -Method Put -Uri http://localhost:8000/v1/users/1002 -ContentType "application/json" -Body '{
  "id": 1002,
  "username": "seller",
  "first_name": "Seller",
  "phone_number": "+251900000002"
}'
```

Create channel admin:

```powershell
Invoke-RestMethod -Method Put -Uri http://localhost:8000/v1/users/1003 -ContentType "application/json" -Body '{
  "id": 1003,
  "username": "admin",
  "first_name": "Admin",
  "phone_number": "+251900000003"
}'
```

Register channel:

```powershell
Invoke-RestMethod -Method Put -Uri http://localhost:8000/v1/channels/-1001234567890 -ContentType "application/json" -Body '{
  "id": -1001234567890,
  "admin_id": 1003,
  "channel_name": "Addis Deals",
  "payout_account_type": "TELEBIRR",
  "payout_account_number": "0911000000"
}'
```

Create escrow and store the response:

```powershell
$escrow = Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/escrows -ContentType "application/json" -Body '{
  "buyer_id": 1001,
  "seller_id": 1002,
  "channel_id": -1001234567890,
  "item_title": "iPhone 14 Pro Max",
  "item_price_etb": "3000.00"
}'
$escrow
```

Expected:

```text
current_state = INITIATED
escrow_fee_etb = 75.00
gateway_fee_etb = 60.00
admin_cut_etb = 6.00
seller_net_etb = 3000.00
```

Confirm terms:

```powershell
$escrow = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/escrows/$($escrow.id)/confirm-terms?changed_by=1001"
$escrow
```

Expected:

```text
current_state = WAITING_FOR_PAYMENT
chapa_reference = nexus-{escrow_id}
```

Simulate Chapa success webhook:

```powershell
$secret = "change-this-to-your-CHAPA_WEBHOOK_SECRET"
$body = @{
  tx_ref = $escrow.chapa_reference
  status = "success"
} | ConvertTo-Json -Compress

$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($secret)
$hashBytes = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($body))
$signature = [BitConverter]::ToString($hashBytes).Replace("-", "").ToLower()

Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/webhooks/chapa -ContentType "application/json" -Headers @{
  "x-chapa-signature" = $signature
} -Body $body

$escrow = Invoke-RestMethod http://localhost:8000/v1/escrows/$($escrow.id)
$escrow
```

Expected:

```text
current_state = PAID
payment_completed_at is not null
```

Submit shipping:

```powershell
$escrow = Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/escrows/$($escrow.id)/ship -ContentType "application/json" -Body '{
  "seller_id": 1002,
  "tracking_id": "TRACK-123",
  "shipping_proof_url": "https://example.com/proof.jpg"
}'
$escrow
```

Expected:

```text
current_state = SHIPPED
tracking_id = TRACK-123
auto_release_at is not null
```

Happy path release:

```powershell
$escrow = Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/escrows/$($escrow.id)/confirm-receipt -ContentType "application/json" -Body '{
  "buyer_id": 1001
}'
$escrow
```

Expected:

```text
current_state = RELEASED
resolved_at is not null
```

Dispute path confirmation should be tested with a fresh escrow. Repeat user/channel creation only if the database was reset. Move the fresh escrow to `SHIPPED`, then file a dispute:

```powershell
$escrow = Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/escrows/$($escrow.id)/dispute -ContentType "application/json" -Body '{
  "buyer_id": 1001,
  "reason": "The received item does not match the listing.",
  "unboxing_video_url": "https://example.com/unboxing.mp4"
}'
$escrow
```

Expected:

```text
current_state = DISPUTED
unboxing_video_url is stored
```

Admin refund:

```powershell
$escrow = Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/escrows/$($escrow.id)/resolve/refund -ContentType "application/json" -Body '{
  "admin_id": 1003,
  "reason": "Buyer evidence confirms item mismatch."
}'
$escrow
```

Expected:

```text
current_state = REFUNDED
resolved_at is not null
```

## E2E Pass Criteria

The system is end-to-end functional when:

- Frontend loads at `http://localhost:5173`.
- Backend docs load at `http://localhost:8000/docs`.
- `/v1/health/ready` returns `ready`.
- Buyer, seller, and admin can be created.
- Channel can be registered.
- Escrow can be created with correct fees.
- Terms confirmation creates a Chapa reference.
- Signed webhook moves escrow to `PAID`.
- Seller shipping moves escrow to `SHIPPED`.
- Buyer confirmation moves escrow to `RELEASED`.
- Separate dispute flow moves `SHIPPED -> DISPUTED -> REFUNDED` or `RELEASED`.
- Invalid actor calls fail, such as seller trying to confirm receipt.
- Invalid state transitions return conflict responses.
- Worker is running and receives auto-release tasks.

## Release Gates

Do not deploy unless these pass:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check-project.ps1
```

For staging and production, also require:

- Migrations tested against a database snapshot.
- Chapa sandbox webhook verified.
- Telegram test bot launch verified.
- Redis worker queue verified.
- Rollback command documented for the exact release.


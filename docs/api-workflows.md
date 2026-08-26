# API Workflows

This document records the current backend contract and the expected order of operations.

## Health

Liveness:

```http
GET /v1/health
```

Readiness:

```http
GET /v1/health/ready
```

Readiness checks PostgreSQL and Redis. Use it for deploy health checks, not for cheap load balancer pings.

## Users

Create or update a Telegram user:

```http
PUT /v1/users/{user_id}
```

Body:

```json
{
  "id": 1001,
  "username": "buyer",
  "first_name": "Buyer",
  "phone_number": "+251900000001"
}
```

Read a user:

```http
GET /v1/users/{user_id}
```

## Channels

Register or update a Telegram channel:

```http
PUT /v1/channels/{channel_id}
```

Body:

```json
{
  "id": -1001234567890,
  "admin_id": 1001,
  "channel_name": "Addis Deals",
  "payout_account_type": "TELEBIRR",
  "payout_account_number": "0911000000"
}
```

Read a channel:

```http
GET /v1/channels/{channel_id}
```

## Escrows

Create escrow:

```http
POST /v1/escrows
```

Body:

```json
{
  "buyer_id": 1001,
  "seller_id": 1002,
  "channel_id": -1001234567890,
  "item_title": "iPhone 14 Pro Max",
  "item_price_etb": "3000.00"
}
```

Rules:

- Buyer must exist.
- Seller must exist.
- Channel must exist when `channel_id` is provided.
- No user balance is created or stored.
- Fees are calculated with decimal arithmetic.

Confirm terms:

```http
POST /v1/escrows/{escrow_id}/confirm-terms?changed_by=1001
```

Effect:

- `INITIATED -> WAITING_FOR_PAYMENT`
- Assigns `chapa_reference` as `nexus-{escrow_id}`.
- Writes an audit log row.

Chapa payment webhook:

```http
POST /v1/webhooks/chapa
```

Required header:

```text
x-chapa-signature: <hmac-sha256>
```

Effect for successful payment:

- Verifies HMAC over the raw request body.
- Finds escrow by `tx_ref`.
- Uses row locking.
- Moves `WAITING_FOR_PAYMENT -> PAID`.

Seller submits shipping:

```http
POST /v1/escrows/{escrow_id}/ship
```

Body:

```json
{
  "seller_id": 1002,
  "tracking_id": "TRACK-123",
  "shipping_proof_url": "https://example.com/proof.jpg"
}
```

Effect:

- `PAID -> SHIPPED`
- Stores tracking and proof URL.
- Sets `auto_release_at`.
- Schedules Celery task `tasks.process_auto_release`.

Buyer confirms receipt:

```http
POST /v1/escrows/{escrow_id}/confirm-receipt
```

Body:

```json
{
  "buyer_id": 1001
}
```

Effect:

- `SHIPPED -> RELEASED`
- Sets `resolved_at`.

Buyer files dispute:

```http
POST /v1/escrows/{escrow_id}/dispute
```

Body:

```json
{
  "buyer_id": 1001,
  "reason": "The received item does not match the listing.",
  "unboxing_video_url": "https://example.com/unboxing.mp4"
}
```

Effect:

- `SHIPPED -> DISPUTED`
- Stores unboxing media URL when provided.

Admin releases to seller:

```http
POST /v1/escrows/{escrow_id}/resolve/release
```

Body:

```json
{
  "admin_id": 1001,
  "reason": "Seller proof is valid and buyer evidence is insufficient."
}
```

Effect:

- `DISPUTED -> RELEASED`
- Also supports valid release from `SHIPPED`.
- Admin must match the escrow channel admin when a channel is attached.

Admin refunds buyer:

```http
POST /v1/escrows/{escrow_id}/resolve/refund
```

Body:

```json
{
  "admin_id": 1001,
  "reason": "Buyer evidence confirms item mismatch."
}
```

Effect:

- `DISPUTED -> REFUNDED`
- Admin must match the escrow channel admin when a channel is attached.

## Current State Machine

```text
INITIATED
  -> WAITING_FOR_PAYMENT
WAITING_FOR_PAYMENT
  -> PAID
  -> REFUNDED
PAID
  -> SHIPPED
  -> REFUNDED
SHIPPED
  -> DISPUTED
  -> RELEASED
DISPUTED
  -> RELEASED
  -> REFUNDED
RELEASED
  -> terminal
REFUNDED
  -> terminal
```

All state changes must go through `EscrowService._transition()` so invalid transitions are rejected and audit logs stay consistent.


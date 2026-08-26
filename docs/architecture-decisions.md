# Architecture Decisions

## Zero-Balance Escrow Orchestration

Nexus records escrow workflow state but does not maintain user wallet balances. Payment custody, settlement, and payout splits are delegated to Chapa. Database records are operational facts, not stored value.

## State Machine First

Escrows move through a strict state machine:

`INITIATED -> WAITING_FOR_PAYMENT -> PAID -> SHIPPED -> RELEASED`

Disputes branch from `SHIPPED` to `DISPUTED`, then terminate at `RELEASED` or `REFUNDED`. Refunds can also terminate from `WAITING_FOR_PAYMENT` or `PAID` when the business rules allow it.

Every state change writes an immutable audit log row in the same database transaction.

## Concurrency

State-changing operations are designed around database row locking through `SELECT ... FOR UPDATE`. Redis can be added at the service edge for coarse locks and rate limits, but PostgreSQL remains the source of truth.

## External Integrations

Chapa and Telegram are isolated behind service modules. API routers should not embed signing, hashing, payout, or bot logic directly.


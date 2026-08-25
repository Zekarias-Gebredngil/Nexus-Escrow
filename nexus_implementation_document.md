# Institutional-Grade Technical & Operational Specification
## Project Nexus: Telegram Micro-Escrow Platform (Ethiopia)
**Version:** 1.0.0  
**Target Architecture:** Solo Developer Execution  
**Regulatory Context:** National Bank of Ethiopia (NBE) Compliant Architecture via Gateway Intermediation  

---

## 1. Executive Summary & Legal/Regulatory Engineering

### 1.1 Regulatory Guardrails (NBE Compliance)
Operating a closed or open loop storage of value without a Payment Instrument Issuer license from the National Bank of Ethiopia (NBE) is a criminal offense under Proclamation No. 718/2011. To completely offload regulatory and compliance risk, Project Nexus implements a **Zero-Balance Holding Architecture**. 

1. **Funds Intermediation:** The platform never maintains an internal custodial balance or dedicated bank settlement account for users. 
2. **Gateway Custody:** All buyer funds are directed into a regulated escrow/settlement account managed directly by Chapa Financial Technologies Inc.
3. **Programmatic Payouts:** Funds are moved from Chapa's pool directly to the seller or channel admin accounts via programmatic webhooks.
4. **Legal Status:** Legally, the system operates purely as a software orchestration engine, functioning as an Independent Sales Organization (ISO) and software integration partner to Chapa.

### 1.2 Know Your Customer (KYC) & Identity Mapping
To prevent money laundering, fraud, and structured structural abuse:
* **Telegram Phone Verification:** The Telegram Web App (TWA) forces a phone number share via the native Telegram API (`reply_markup` with `request_contact=True`).
* **Cross-Gateway Verification:** The verified Telegram phone number is bound to the transaction profile. Before disbursing funds via Chapa's Payout API, the destination Telebirr, M-Pesa, or CBE Birr account holder identity is verified using Chapa's account verification endpoint to guarantee it matches the transaction records.

---

## 2. System Architecture & The Secure State Machine

### 2.1 Technical Stack Summary
* **Frontend:** React 19 (TypeScript) + Vite + TailwindCSS. Managed via Telegram Web App (TWA) SDK.
* **Backend:** Python 3.11 + FastAPI (Asynchronous execution model utilizing Uvicorn/Gunicorn).
* **Database:** PostgreSQL 15. Absolute ACID compliance, strict transaction isolation levels.
* **Cache & Locks:** Redis Stack (Used for distributed locking, rate limiting, and session cache).
* **Worker Queue:** Celery + Redis (For processing background timeouts, automated releases, and webhook retries).

### 2.2 Database Schema (DDL)
```sql
-- Enums for Explicit State Control
CREATE TYPE escrow_state AS ENUM (
    'INITIATED', 
    'WAITING_FOR_PAYMENT', 
    'PAID', 
    'SHIPPED', 
    'DISPUTED', 
    'RELEASED', 
    'REFUNDED'
);

-- Users Table
CREATE TABLE users (
    id BIGINT PRIMARY KEY, -- Maps directly to Telegram User ID
    username VARCHAR(100),
    first_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    reputation_score NUMERIC(3,2) DEFAULT 5.00,
    total_escrows_completed INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Channels/Admins Table
CREATE TABLE channels (
    id BIGINT PRIMARY KEY, -- Telegram Channel ID
    admin_id BIGINT REFERENCES users(id),
    channel_name VARCHAR(250) NOT NULL,
    payout_account_type VARCHAR(50) NOT NULL, -- TELEBIRR, CBE, MPESA
    payout_account_number VARCHAR(50) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Escrow Transactions Table
CREATE TABLE escrows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id BIGINT REFERENCES users(id) NOT NULL,
    seller_id BIGINT REFERENCES users(id) NOT NULL,
    channel_id BIGINT REFERENCES channels(id),
    item_title VARCHAR(255) NOT NULL,
    item_price_etb NUMERIC(12, 2) NOT NULL,
    gateway_fee_etb NUMERIC(12, 2) NOT NULL,
    escrow_fee_etb NUMERIC(12, 2) NOT NULL,
    admin_cut_etb NUMERIC(12, 2) NOT NULL,
    seller_net_etb NUMERIC(12, 2) NOT NULL,
    current_state escrow_state DEFAULT 'INITIATED' NOT NULL,
    chapa_reference VARCHAR(100) UNIQUE,
    tracking_id VARCHAR(100),
    shipping_proof_url TEXT,
    unboxing_video_url TEXT,
    payment_completed_at TIMESTAMP WITH TIME ZONE,
    shipped_at TIMESTAMP WITH TIME ZONE,
    auto_release_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- State Audit Log for Immutable Ledger
CREATE TABLE escrow_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    escrow_id UUID REFERENCES escrows(id) NOT NULL,
    from_state escrow_state NOT NULL,
    to_state escrow_state NOT NULL,
    changed_by BIGINT REFERENCES users(id),
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 Strict State Machine & Race Condition Prevention
To prevent race conditions (such as a user calling for a refund concurrently while a background task releases funds), the backend must utilize PostgreSQL `SELECT FOR UPDATE` or distributed Redis locks. 

```
                       +---------------+
                       |   INITIATED   |
                       +-------+-------+
                               | Buyer confirms terms
                               v
                   +-----------------------+
                   |  WAITING_FOR_PAYMENT  |
                   +-------+---------------+
                           | Chapa Webhook Received (Signed)
                           v
                       +-------+-------+
                       |     PAID      |
                       +-------+-------+
                               | Seller ships & inputs tracking
                               v
                       +-------+-------+
                       |    SHIPPED    |
                       +---+-------+---+
      Buyer raises dispute |       | Buyer confirms receipt OR 48hr timeout
                           v       v
            +----------+-----+   +------------+
            |    DISPUTED    |   |  RELEASED  |
            +----------+-----+   +------------+
                       |         (Triggers Payout Split API)
          Admin ruling |
          +------------+------------+
          |                         |
          v                         v
   +------------+            +------------+
   |  RELEASED  |            |  REFUNDED  |
   +------------+            +------------+
```

---

## 3. Financial Engineering & Monetization Architecture

### 3.1 Fee Matrix Formulation
Chapa charges a standard processing fee for local payments (typically 2.0% to 3.5%). The platform overlays a **Total Transaction Overhead** of 2.5%, which absorbs the payment gateway costs and structures the platform's revenue split.

**Financial Distribution Breakdown for a 3,000 ETB Transaction Example:**
* **Item Value (Gross):** 3,000.00 ETB
* **Total Cost to Buyer:** 3,075.00 ETB (Item Price + 2.5% Escrow Fee)
* **Escrow Processing Pool:** 75.00 ETB
    * *Chapa Processing Fee (approx 2%):* 60.00 ETB
    * *Platform Net Fee:* 15.00 ETB
        * **Platform Revenue (60% of Net):** 9.00 ETB
        * **Channel Admin Commision (40% of Net):** 6.00 ETB
* **Seller Disbursement:** 3,000.00 ETB

### 3.2 Programmatic Split Realization via Chapa API
Rather than executing manual payouts, payouts utilize Chapa's Multi-Account Split mechanism passed during transaction initialization (`/v1/transaction/initialize`):

```json
{
  "amount": "3075.00",
  "currency": "ETB",
  "email": "buyer@telegram.com",
  "first_name": "TelegramUser",
  "last_name": "Buyer",
  "tx_ref": "nexus-escrow-uuid-xyz",
  "callback_url": "https://api.nexus-escrow.com/v1/webhooks/chapa",
  "subaccounts": [
    {
      "id": "acct_seller_chapa_id",
      "split_value": 3000.00
    },
    {
      "id": "acct_admin_chapa_id",
      "split_value": 6.00
    }
  ]
}
```
*Note: The platform's net share remains in the primary Chapa merchant ledger automatically.*

---

## 4. Security Hardening & Webhook Verification

### 4.1 Cryptographic Webhook Validation (Python FastAPI Implementation)
Every payment confirmation from Chapa must be strictly verified before altering database state.

```python
import hmac
import hashlib
import json
from fastapi import Request, HTTPException, Header, Depends
from sqlalchemy.orm import Session
from database import get_db, EscrowTable, EscrowState

CHAPA_SECRET_KEY = "CHASEC_PROD_YOUR_SECRET_KEY_HERE"

async def verify_chapa_webhook(
    request: Request, 
    x_chapa_signature: str = Header(None)
):
    if not x_chapa_signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")
    
    body = await request.body()
    
    # Generate HMAC-SHA256 signature
    computed_signature = hmac.new(
        CHAPA_SECRET_KEY.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(computed_signature, x_chapa_signature):
        raise HTTPException(status_code=403, detail="Invalid cryptographic signature")
    
    return json.loads(body)

@app.post("/v1/webhooks/chapa")
async def handle_chapa_webhook(
    payload: dict = Depends(verify_chapa_webhook), 
    db: Session = Depends(get_db)
):
    tx_ref = payload.get("tx_ref")
    status = payload.get("status")
    
    if status == "success":
        # Concurrently lock row to prevent transactional race conditions
        escrow = db.query(EscrowTable).filter(
            EscrowTable.chapa_reference == tx_ref
        ).with_for_update().first()
        
        if escrow and escrow.current_state == EscrowState.WAITING_FOR_PAYMENT:
            escrow.current_state = EscrowState.PAID
            escrow.payment_completed_at = datetime.utcnow()
            db.commit()
            
            # Trigger asynchronous Telegram Push Notification to Seller
            celery_app.send_task("tasks.notify_seller_paid", args=[escrow.id])
            
    return {"status": "received"}
```

---

## 5. Operations & The Automated Dispute Framework

### 5.1 The 48-Hour Asynchronous Escrow Lifecycle
To optimize operations for a single developer, handling timers via explicit cron checks or background loop architectures is required:
1. When a seller marks an item as `SHIPPED`, a Celery worker initializes a delayed task:
   `process_auto_release.apply_async(args=[escrow_id], countdown=172800)` (48 hours).
2. If the buyer checks a confirmation button within the TWA prior to expiration, the worker instance exits gracefully via defensive checking of state states (`if status != 'SHIPPED': return`).

### 5.2 Decoupled Self-Service Arbitration Engine
When a buyer selects "File Dispute", the transaction enters the `DISPUTED` state. The TWA interface adapts dynamically:
* **The Buyer View:** Explicitly requests an unboxing media link or detailed pictorial upload indicating damages or counterfeit status.
* **The Seller View:** Explicitly requests a valid regional transit manifest (Anbessa Bus slip, localized delivery driver receipt note, or postal dispatch documentation).
* **The Admin Dashboard:** Built utilizing **Retool** or clean static boilerplate. Compiles tracking history, transaction specifics, and media links onto a single screen with two primary terminal operational buttons: `[Authorize Full Refund]` or `[Disburse to Seller]`.

---

## 6. Channel Admin Acquisition and Integration Engine

### 6.1 Inline Deployment via Telegram Bot API
To minimize customer acquisition costs (CAC), channel admins are provided with an inline interactive integration toolkit.
1. Admin opens the Nexus Bot and completes configuration (`/setup_channel`).
2. The bot requests the Admin’s preferred payout account (Telebirr/CBE).
3. The Admin adds the Nexus Bot into their public Telegram Channel with permissions restricted solely to `Post Messages`.
4. **Automated Conversion Injector:** The admin crafts a post describing an item using standard syntax or the bot's generation tool. The bot parses text structures and automatically binds a native Telegram inline URL pointing directly to the TWA configuration:
   `https://t.me/NexusEscrowBot/app?startapp=escrow_id_xyz`

This transforms standard conversational text channels into an interactive, cryptographically secured digital marketplace.

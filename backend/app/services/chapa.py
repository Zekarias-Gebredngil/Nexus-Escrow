import hashlib
import hmac
import json
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.models.escrow import Escrow


class ChapaWebhookVerifier:
    def verify(self, *, body: bytes, signature: str | None) -> dict[str, Any]:
        if not signature:
            raise HTTPException(status_code=401, detail="Missing webhook signature")

        expected = hmac.new(
            settings.chapa_webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

        return json.loads(body)


class ChapaClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=str(settings.chapa_base_url),
            headers={"Authorization": f"Bearer {settings.chapa_secret_key}"},
            timeout=15.0,
        )

    async def initialize_escrow_payment(self, escrow: Escrow, buyer_email: str) -> dict[str, Any]:
        total = escrow.item_price_etb + escrow.escrow_fee_etb
        payload = {
            "amount": self._money(total),
            "currency": "ETB",
            "email": buyer_email,
            "first_name": "Telegram",
            "last_name": "Buyer",
            "tx_ref": escrow.chapa_reference,
            "callback_url": str(settings.chapa_callback_url),
            "subaccounts": [],
        }
        response = await self._client.post("/v1/transaction/initialize", json=payload)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _money(value: Decimal) -> str:
        return f"{value:.2f}"


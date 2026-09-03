from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.chapa import ChapaWebhookVerifier
from app.services.escrows import EscrowService

router = APIRouter()


@router.post("/chapa")
async def handle_chapa_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_chapa_signature: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    body = await request.body()
    payload = ChapaWebhookVerifier().verify(body=body, signature=x_chapa_signature)

    tx_ref = payload.get("tx_ref")
    status = payload.get("status")
    if not tx_ref:
        raise HTTPException(status_code=422, detail="Missing tx_ref")

    if status == "success":
        await EscrowService(session).mark_paid(chapa_reference=tx_ref)

    return {"status": "received"}

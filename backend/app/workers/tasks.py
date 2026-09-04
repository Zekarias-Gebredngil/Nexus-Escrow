import asyncio
from uuid import UUID

from app.db.session import SessionLocal
from app.services.escrows import EscrowService
from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.process_auto_release")
def process_auto_release(escrow_id: str) -> None:
    asyncio.run(_process_auto_release(UUID(escrow_id)))


async def _process_auto_release(escrow_id: UUID) -> None:
    async with SessionLocal() as session:
        await EscrowService(session).auto_release(escrow_id)


@celery_app.task(name="tasks.notify_seller_paid")
def notify_seller_paid(escrow_id: str) -> None:
    # Placeholder: send Telegram notification once bot token and message templates are configured.
    return None


from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.channel import Channel
from app.models.escrow import Escrow, EscrowAuditLog, EscrowState
from app.models.user import User
from app.schemas.escrow import AdminResolution, DisputeSubmission, EscrowCreate, ShippingSubmission
from app.services.fees import FeeCalculator
from app.services.state_machine import can_transition


class InvalidTransition(Exception):
    pass


class EscrowService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: EscrowCreate) -> Escrow:
        await self._require_user(payload.buyer_id, role="buyer")
        await self._require_user(payload.seller_id, role="seller")
        if payload.channel_id is not None:
            await self._require_channel(payload.channel_id)

        fees = FeeCalculator().calculate(payload.item_price_etb)
        escrow = Escrow(
            buyer_id=payload.buyer_id,
            seller_id=payload.seller_id,
            channel_id=payload.channel_id,
            item_title=payload.item_title,
            item_price_etb=payload.item_price_etb,
            gateway_fee_etb=fees.gateway_fee_etb,
            escrow_fee_etb=fees.escrow_fee_etb,
            admin_cut_etb=fees.admin_cut_etb,
            seller_net_etb=fees.seller_net_etb,
        )
        self.session.add(escrow)
        await self.session.commit()
        await self.session.refresh(escrow)
        return escrow

    async def get(self, escrow_id: UUID) -> Escrow | None:
        return await self.session.get(Escrow, escrow_id)

    async def list_for_user(self, user_id: int, limit: int = 50) -> list[Escrow]:
        stmt = (
            select(Escrow)
            .where((Escrow.buyer_id == user_id) | (Escrow.seller_id == user_id))
            .order_by(Escrow.created_at.desc())
            .limit(limit)
        )
        return list(await self.session.scalars(stmt))

    async def confirm_terms(self, escrow_id: UUID, changed_by: int) -> Escrow:
        escrow = await self._get_locked(escrow_id)
        self._transition(
            escrow,
            EscrowState.WAITING_FOR_PAYMENT,
            changed_by=changed_by,
            reason="Buyer confirmed escrow terms",
        )
        escrow.chapa_reference = f"nexus-{escrow.id}"
        await self.session.commit()
        await self.session.refresh(escrow)
        return escrow

    async def mark_paid(self, chapa_reference: str) -> Escrow | None:
        stmt = select(Escrow).where(Escrow.chapa_reference == chapa_reference).with_for_update()
        escrow = await self.session.scalar(stmt)
        if escrow is None:
            return None
        if escrow.current_state != EscrowState.WAITING_FOR_PAYMENT:
            return escrow

        self._transition(
            escrow,
            EscrowState.PAID,
            changed_by=None,
            reason="Verified Chapa payment webhook",
        )
        escrow.payment_completed_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(escrow)
        return escrow

    async def mark_shipped(self, escrow_id: UUID, payload: ShippingSubmission) -> Escrow:
        escrow = await self._get_locked(escrow_id)
        if escrow.seller_id != payload.seller_id:
            raise InvalidTransition("Only the seller can mark this escrow as shipped")
        self._transition(
            escrow,
            EscrowState.SHIPPED,
            changed_by=payload.seller_id,
            reason="Seller submitted tracking and proof of shipment",
        )
        escrow.tracking_id = payload.tracking_id
        escrow.shipping_proof_url = str(payload.shipping_proof_url)
        escrow.shipped_at = datetime.now(UTC)
        escrow.auto_release_at = escrow.shipped_at + timedelta(hours=settings.auto_release_hours)
        await self.session.commit()
        await self.session.refresh(escrow)

        from app.workers.tasks import process_auto_release

        process_auto_release.apply_async(
            args=[str(escrow.id)],
            countdown=settings.auto_release_hours * 60 * 60,
        )
        return escrow

    async def confirm_receipt(self, escrow_id: UUID, changed_by: int) -> Escrow:
        escrow = await self._get_locked(escrow_id)
        if escrow.buyer_id != changed_by:
            raise InvalidTransition("Only the buyer can confirm receipt")
        return await self._release(
            escrow,
            changed_by=changed_by,
            reason="Buyer confirmed receipt",
        )

    async def file_dispute(self, escrow_id: UUID, payload: DisputeSubmission) -> Escrow:
        escrow = await self._get_locked(escrow_id)
        if escrow.buyer_id != payload.buyer_id:
            raise InvalidTransition("Only the buyer can dispute this escrow")

        self._transition(
            escrow,
            EscrowState.DISPUTED,
            changed_by=payload.buyer_id,
            reason=payload.reason,
        )
        if payload.unboxing_video_url is not None:
            escrow.unboxing_video_url = str(payload.unboxing_video_url)
        await self.session.commit()
        await self.session.refresh(escrow)
        return escrow

    async def resolve_to_seller(self, escrow_id: UUID, payload: AdminResolution) -> Escrow:
        escrow = await self._get_locked(escrow_id)
        await self._require_admin_authorized(escrow, payload.admin_id)
        return await self._release(
            escrow,
            changed_by=payload.admin_id,
            reason=f"Admin resolved to seller: {payload.reason}",
        )

    async def refund_buyer(self, escrow_id: UUID, payload: AdminResolution) -> Escrow:
        escrow = await self._get_locked(escrow_id)
        await self._require_admin_authorized(escrow, payload.admin_id)
        self._transition(
            escrow,
            EscrowState.REFUNDED,
            changed_by=payload.admin_id,
            reason=f"Admin authorized refund: {payload.reason}",
        )
        escrow.resolved_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(escrow)
        return escrow

    async def auto_release(self, escrow_id: UUID) -> Escrow | None:
        escrow = await self._get_locked(escrow_id)
        if escrow.current_state != EscrowState.SHIPPED:
            return escrow
        return await self._release(
            escrow,
            changed_by=None,
            reason="Auto release timeout elapsed",
        )

    async def _get_locked(self, escrow_id: UUID) -> Escrow:
        stmt = select(Escrow).where(Escrow.id == escrow_id).with_for_update()
        escrow = await self.session.scalar(stmt)
        if escrow is None:
            raise InvalidTransition("Escrow not found")
        return escrow

    async def _require_user(self, user_id: int, *, role: str) -> None:
        user = await self.session.get(User, user_id)
        if user is None:
            raise InvalidTransition(f"Unknown {role} user")

    async def _require_channel(self, channel_id: int) -> Channel:
        channel = await self.session.get(Channel, channel_id)
        if channel is None:
            raise InvalidTransition("Unknown channel")
        return channel

    async def _require_admin_authorized(self, escrow: Escrow, admin_id: int) -> None:
        if escrow.channel_id is None:
            return
        channel = await self._require_channel(escrow.channel_id)
        if channel.admin_id != admin_id:
            raise InvalidTransition("Admin is not authorized to resolve this escrow")

    async def _release(
        self,
        escrow: Escrow,
        *,
        changed_by: int | None,
        reason: str,
    ) -> Escrow:
        self._transition(
            escrow,
            EscrowState.RELEASED,
            changed_by=changed_by,
            reason=reason,
        )
        escrow.resolved_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(escrow)
        return escrow

    def _transition(
        self,
        escrow: Escrow,
        to_state: EscrowState,
        *,
        changed_by: int | None,
        reason: str,
    ) -> None:
        from_state = escrow.current_state
        if not can_transition(from_state, to_state):
            raise InvalidTransition(f"Cannot transition escrow from {from_state} to {to_state}")

        escrow.current_state = to_state
        self.session.add(
            EscrowAuditLog(
                escrow_id=escrow.id,
                from_state=from_state,
                to_state=to_state,
                changed_by=changed_by,
                reason=reason,
            )
        )

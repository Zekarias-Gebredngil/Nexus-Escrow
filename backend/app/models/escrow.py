from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EscrowState(StrEnum):
    INITIATED = "INITIATED"
    WAITING_FOR_PAYMENT = "WAITING_FOR_PAYMENT"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DISPUTED = "DISPUTED"
    RELEASED = "RELEASED"
    REFUNDED = "REFUNDED"


class Escrow(Base):
    __tablename__ = "escrows"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"))
    item_title: Mapped[str] = mapped_column(String(255))
    item_price_etb: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    gateway_fee_etb: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    escrow_fee_etb: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    admin_cut_etb: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    seller_net_etb: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    current_state: Mapped[EscrowState] = mapped_column(
        Enum(EscrowState, name="escrow_state"),
        default=EscrowState.INITIATED,
    )
    chapa_reference: Mapped[str | None] = mapped_column(String(100), unique=True)
    tracking_id: Mapped[str | None] = mapped_column(String(100))
    shipping_proof_url: Mapped[str | None] = mapped_column(Text)
    unboxing_video_url: Mapped[str | None] = mapped_column(Text)
    payment_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auto_release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    audit_logs = relationship(
        "EscrowAuditLog",
        back_populates="escrow",
        cascade="all, delete-orphan",
    )


class EscrowAuditLog(Base):
    __tablename__ = "escrow_audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    escrow_id: Mapped[UUID] = mapped_column(ForeignKey("escrows.id"), nullable=False)
    from_state: Mapped[EscrowState] = mapped_column(Enum(EscrowState, name="escrow_state"))
    to_state: Mapped[EscrowState] = mapped_column(Enum(EscrowState, name="escrow_state"))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    escrow = relationship("Escrow", back_populates="audit_logs")

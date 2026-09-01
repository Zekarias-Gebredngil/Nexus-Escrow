from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.escrow import EscrowState


class EscrowCreate(BaseModel):
    buyer_id: int
    seller_id: int
    channel_id: int | None = None
    item_title: str = Field(min_length=3, max_length=255)
    item_price_etb: Decimal = Field(gt=0, decimal_places=2)


class ShippingSubmission(BaseModel):
    seller_id: int
    tracking_id: str = Field(min_length=3, max_length=100)
    shipping_proof_url: HttpUrl


class ReceiptConfirmation(BaseModel):
    buyer_id: int


class DisputeSubmission(BaseModel):
    buyer_id: int
    reason: str = Field(min_length=10, max_length=2000)
    unboxing_video_url: HttpUrl | None = None


class AdminResolution(BaseModel):
    admin_id: int
    reason: str = Field(min_length=10, max_length=2000)


class EscrowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    buyer_id: int
    seller_id: int
    channel_id: int | None
    item_title: str
    item_price_etb: Decimal
    gateway_fee_etb: Decimal
    escrow_fee_etb: Decimal
    admin_cut_etb: Decimal
    seller_net_etb: Decimal
    current_state: EscrowState
    chapa_reference: str | None
    tracking_id: str | None
    shipping_proof_url: str | None
    unboxing_video_url: str | None
    payment_completed_at: datetime | None
    shipped_at: datetime | None
    auto_release_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime

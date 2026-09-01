from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PayoutAccountType(StrEnum):
    TELEBIRR = "TELEBIRR"
    CBE = "CBE"
    MPESA = "MPESA"


class ChannelCreate(BaseModel):
    id: int
    admin_id: int
    channel_name: str = Field(min_length=2, max_length=250)
    payout_account_type: PayoutAccountType
    payout_account_number: str = Field(min_length=5, max_length=50)


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_id: int
    channel_name: str
    payout_account_type: str
    payout_account_number: str
    is_verified: bool
    created_at: datetime


from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class UserUpsert(BaseModel):
    id: int
    username: str | None = Field(default=None, max_length=100)
    first_name: str = Field(min_length=1, max_length=150)
    phone_number: str = Field(min_length=7, max_length=20)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None
    first_name: str
    phone_number: str
    reputation_score: Decimal
    total_escrows_completed: int
    created_at: datetime


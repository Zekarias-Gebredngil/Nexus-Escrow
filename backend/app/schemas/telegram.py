from pydantic import BaseModel, ConfigDict


class TelegramInitData(BaseModel):
    init_data: str


class TelegramInitUser(BaseModel):
    id: int
    first_name: str
    username: str | None = None
    phone_number: str


class TelegramUserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None
    first_name: str
    phone_number: str


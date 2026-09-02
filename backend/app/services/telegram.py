import hashlib
import hmac
import json
from urllib.parse import parse_qsl

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.schemas.telegram import TelegramInitUser


class TelegramAuthService:
    def verify_init_data(self, init_data: str) -> TelegramInitUser:
        values = dict(parse_qsl(init_data, keep_blank_values=True))
        supplied_hash = values.pop("hash", None)
        if not supplied_hash:
            raise HTTPException(status_code=401, detail="Missing Telegram auth hash")

        data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
        secret_key = hmac.new(
            b"WebAppData",
            settings.telegram_bot_token.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, supplied_hash):
            raise HTTPException(status_code=403, detail="Invalid Telegram init data")

        user_payload = json.loads(values["user"])
        if "phone_number" not in user_payload:
            raise HTTPException(status_code=428, detail="Telegram contact sharing is required")
        return TelegramInitUser.model_validate(user_payload)


class TelegramUserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_from_init_data(self, telegram_user: TelegramInitUser) -> User:
        user = await self.session.get(User, telegram_user.id)
        if user is None:
            user = User(
                id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                phone_number=telegram_user.phone_number,
            )
            self.session.add(user)
        else:
            user.username = telegram_user.username
            user.first_name = telegram_user.first_name
            user.phone_number = telegram_user.phone_number

        await self.session.commit()
        await self.session.refresh(user)
        return user


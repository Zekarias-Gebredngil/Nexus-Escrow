from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.telegram import TelegramInitData, TelegramUserProfile
from app.services.telegram import TelegramAuthService, TelegramUserService

router = APIRouter()


@router.post("/session", response_model=TelegramUserProfile)
async def create_twa_session(
    payload: TelegramInitData,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TelegramUserProfile:
    telegram_user = TelegramAuthService().verify_init_data(payload.init_data)
    user = await TelegramUserService(session).upsert_from_init_data(telegram_user)
    return TelegramUserProfile.model_validate(user)

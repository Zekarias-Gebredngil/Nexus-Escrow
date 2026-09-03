from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.channel import ChannelCreate, ChannelRead
from app.services.channels import ChannelService

router = APIRouter()


@router.put("/{channel_id}", response_model=ChannelRead)
async def register_channel(
    channel_id: int,
    payload: ChannelCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChannelRead:
    if channel_id != payload.id:
        raise HTTPException(status_code=422, detail="Path channel_id must match payload id")
    channel = await ChannelService(session).register(payload)
    return ChannelRead.model_validate(channel)


@router.get("/{channel_id}", response_model=ChannelRead)
async def get_channel(
    channel_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChannelRead:
    channel = await ChannelService(session).get(channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return ChannelRead.model_validate(channel)


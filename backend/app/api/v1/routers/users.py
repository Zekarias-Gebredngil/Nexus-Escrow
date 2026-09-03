from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.user import UserRead, UserUpsert
from app.services.users import UserService

router = APIRouter()


@router.put("/{user_id}", response_model=UserRead)
async def upsert_user(
    user_id: int,
    payload: UserUpsert,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRead:
    if user_id != payload.id:
        raise HTTPException(status_code=422, detail="Path user_id must match payload id")
    user = await UserService(session).upsert(payload)
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRead:
    user = await UserService(session).get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(user)


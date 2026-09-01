from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserUpsert


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, payload: UserUpsert) -> User:
        user = await self.session.get(User, payload.id)
        if user is None:
            user = User(
                id=payload.id,
                username=payload.username,
                first_name=payload.first_name,
                phone_number=payload.phone_number,
            )
            self.session.add(user)
        else:
            user.username = payload.username
            user.first_name = payload.first_name
            user.phone_number = payload.phone_number

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)


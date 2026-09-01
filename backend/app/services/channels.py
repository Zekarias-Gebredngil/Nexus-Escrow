from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.schemas.channel import ChannelCreate


class ChannelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, payload: ChannelCreate) -> Channel:
        channel = await self.session.get(Channel, payload.id)
        if channel is None:
            channel = Channel(
                id=payload.id,
                admin_id=payload.admin_id,
                channel_name=payload.channel_name,
                payout_account_type=payload.payout_account_type.value,
                payout_account_number=payload.payout_account_number,
            )
            self.session.add(channel)
        else:
            channel.admin_id = payload.admin_id
            channel.channel_name = payload.channel_name
            channel.payout_account_type = payload.payout_account_type.value
            channel.payout_account_number = payload.payout_account_number

        await self.session.commit()
        await self.session.refresh(channel)
        return channel

    async def get(self, channel_id: int) -> Channel | None:
        return await self.session.get(Channel, channel_id)


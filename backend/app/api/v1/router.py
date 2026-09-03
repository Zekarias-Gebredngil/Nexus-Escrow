from fastapi import APIRouter

from app.api.v1.routers import channels, escrows, health, telegram, users, webhooks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_router.include_router(escrows.router, prefix="/escrows", tags=["escrows"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

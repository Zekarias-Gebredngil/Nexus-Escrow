from fastapi import APIRouter
from sqlalchemy import text

from app.cache.redis import create_redis_client
from app.db.session import SessionLocal

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))

    redis = create_redis_client()
    try:
        await redis.ping()
    finally:
        await redis.aclose()

    return {"status": "ready"}

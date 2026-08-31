from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(150))
    phone_number: Mapped[str] = mapped_column(String(20), unique=True)
    reputation_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("5.00"))
    total_escrows_completed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    administered_channels = relationship("Channel", back_populates="admin")


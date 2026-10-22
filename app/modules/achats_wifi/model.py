
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WifiPurchase(Base):
    __tablename__ = "wifi_purchases"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"),
        nullable=False,
        index=True,
    )

    wifi_code_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("wifi_codes.id"),
        nullable=False,
        unique=True,
    )

    plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("plans.id"),
        nullable=False,
    )

    price_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="HTG",
    )

    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

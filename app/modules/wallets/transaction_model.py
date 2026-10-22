
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True
    )

    wallet_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("wallets.id"),
        nullable=False,
    )

    type: Mapped[str] = mapped_column(
        String, nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False
    )

    balance_after: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False
    )

    deposit_request_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    order_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    recharge_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

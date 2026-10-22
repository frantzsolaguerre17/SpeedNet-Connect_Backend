
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    duration_hours: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="HTG"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="active", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class WifiCode(Base):
    __tablename__ = "wifi_codes"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True
    )
    plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("plans.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(
        String, nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="available", index=True
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    sold_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

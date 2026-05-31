from sqlalchemy import Enum
from app.db.enums import IntervalType
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.database import Base


class Price(Base):
    __tablename__ = "prices"

    __table_args__ = (
        UniqueConstraint(
            "equity_id",
            "date_time",
            "interval",
            name="uq_equity_datetime_interval"
        ),
    )

    pk_price_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    equity_id: Mapped[int] = mapped_column(
        ForeignKey("equities.pk_equity_id"),
        nullable=False,
        index=True
    )

    date_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True
    )

    interval: Mapped[IntervalType] = mapped_column(
        Enum(IntervalType),
        nullable=False
    )

    open: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    high: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    low: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    close: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    volume: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    dividends: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    stock_splits: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    trades_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
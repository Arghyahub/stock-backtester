from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.database import Base


class Trade(Base):
    __tablename__ = "trades"

    pk_trade_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.pk_strategy_id"),
        nullable=False
    )

    equity_id: Mapped[int] = mapped_column(
        ForeignKey("equities.pk_equity_id"),
        nullable=False
    )

    entry_price_id: Mapped[int | None] = mapped_column(
        ForeignKey("prices.pk_price_id"),
        nullable=True
    )

    exit_price_id: Mapped[int | None] = mapped_column(
        ForeignKey("prices.pk_price_id"),
        nullable=True
    )

    entry_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    exit_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    entry_date_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    exit_date_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    return_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    return_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    window_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    win_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    max_draw_down: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    sharpe_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )
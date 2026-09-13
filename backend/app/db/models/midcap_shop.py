from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MidcapShopPosition(Base):
    __tablename__ = "midcap_shop_positions"
    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_midcap_shop_user_ticker"),)

    pk_midcap_shop_position_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.pk_user_id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    average_cost: Mapped[float] = mapped_column(Float, nullable=False)
    latest_purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    latest_purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_count: Mapped[int] = mapped_column(Integer, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class MidcapShopTradeEvent(Base):
    __tablename__ = "midcap_shop_trade_events"

    pk_midcap_shop_trade_event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.pk_user_id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_price: Mapped[float] = mapped_column(Float, nullable=False)
    execution_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cost_basis: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

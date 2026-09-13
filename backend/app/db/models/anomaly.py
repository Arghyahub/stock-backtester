from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class StrategyRun(Base):
    __tablename__ = "strategy_runs"
    pk_strategy_run_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.pk_strategy_id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="completed")
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    data_quality: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class InstrumentMapping(Base):
    __tablename__ = "instrument_mappings"
    __table_args__ = (UniqueConstraint("sector_equity_id", "instrument_equity_id", name="uq_sector_instrument"),)
    pk_instrument_mapping_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sector_equity_id: Mapped[int] = mapped_column(ForeignKey("equities.pk_equity_id"), nullable=False, index=True)
    instrument_equity_id: Mapped[int] = mapped_column(ForeignKey("equities.pk_equity_id"), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class StrategyPlan(Base):
    __tablename__ = "strategy_plans"
    pk_strategy_plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_run_id: Mapped[int] = mapped_column(ForeignKey("strategy_runs.pk_strategy_run_id", ondelete="CASCADE"), nullable=False, index=True)
    sector_equity_id: Mapped[int] = mapped_column(ForeignKey("equities.pk_equity_id"), nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    oos_observations: Mapped[int] = mapped_column(Integer, nullable=False)
    oos_mean_return: Mapped[float] = mapped_column(Float, nullable=False)
    oos_win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    oos_worst_return: Mapped[float] = mapped_column(Float, nullable=False)
    oos_worst_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class PlanInstrument(Base):
    __tablename__ = "plan_instruments"
    __table_args__ = (UniqueConstraint("strategy_plan_id", "equity_id", name="uq_plan_instrument"),)
    pk_plan_instrument_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_plan_id: Mapped[int] = mapped_column(ForeignKey("strategy_plans.pk_strategy_plan_id", ondelete="CASCADE"), nullable=False, index=True)
    equity_id: Mapped[int] = mapped_column(ForeignKey("equities.pk_equity_id"), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String, nullable=False)
    seasonal_return: Mapped[float] = mapped_column(Float, nullable=False)
    alpha: Mapped[float] = mapped_column(Float, nullable=False)
    beta: Mapped[float] = mapped_column(Float, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_recommended: Mapped[bool] = mapped_column(default=False, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

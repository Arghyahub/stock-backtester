from datetime import datetime
from pydantic import BaseModel, Field


class MappingRequest(BaseModel):
    sector_equity_id: int
    ticker: str
    name: str
    instrument_type: str = Field(pattern="^(STOCK|ETF)$")


class MappingResponse(BaseModel):
    mapping_id: int
    sector_equity_id: int
    instrument_equity_id: int
    ticker: str
    name: str
    instrument_type: str


class PlanInstrumentResponse(BaseModel):
    ticker: str
    name: str
    instrument_type: str
    seasonal_return: float
    alpha: float
    beta: float
    observation_count: int


class PlanSummary(BaseModel):
    plan_id: int
    sector: str
    entry_date: str
    exit_date: str
    window_days: int
    oos_mean_return: float
    oos_win_rate: float
    oos_worst_return: float
    oos_worst_drawdown: float
    stock: PlanInstrumentResponse | None = None
    etf: PlanInstrumentResponse | None = None


class Headline(BaseModel):
    title: str
    url: str
    published_at: str | None = None

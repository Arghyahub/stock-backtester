from datetime import datetime
from app.db.enums import IntervalType
from app.db.enums import EquityType
from pydantic import BaseModel
from app.schemas.index_schema import ReponseModel

class TrackEquityBase(BaseModel):
    ticker: str
    name: str

class TrackEquityRequest(BaseModel):
    equities: list[TrackEquityBase]
    type: EquityType
    interval: IntervalType

class EquitySummary(BaseModel):
    equity_id: int
    name: str
    ticker: str
    start_date: datetime | None
    end_date: datetime | None
    signal_count: int

class EquitySummaryResponse(ReponseModel):
    equities: list[EquitySummary]

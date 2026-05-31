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


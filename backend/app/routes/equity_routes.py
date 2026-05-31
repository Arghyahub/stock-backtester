from app.schemas.equity_schema import EquitySummaryResponse
from app.schemas.equity_schema import EquitySummary
from app.db.enums import EquityType
from app.repositories.equity_repository import EquityRepository
from app.db.database import get_db
from fastapi import Depends
from sqlalchemy.orm import Session
from app.schemas.index_schema import ReponseModel
from app.schemas.equity_schema import TrackEquityRequest
from fastapi import APIRouter

equity_router = APIRouter(
    prefix="/equity",
    tags=["Equity"]
)

@equity_router.post(
    "/track-equities",
    response_model=ReponseModel
)
def track_equity(
    data: TrackEquityRequest,
    db: Session = Depends(get_db)
):
    EquityRepository.create_and_track_equities(db, data)
    return {"message": "Equities tracked successfully", "success": True}

@equity_router.get(
    "/summary",
    response_model=EquitySummaryResponse
)
def get_equity_summary(
    type: EquityType,
    db: Session = Depends(get_db)
):
    equities = EquityRepository.get_equity_summary(db, type.value)
    return {"equities": equities, "success": True, "message": "Equities summary fetched successfully"}


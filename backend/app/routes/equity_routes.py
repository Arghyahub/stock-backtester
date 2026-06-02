from fastapi.responses import JSONResponse
from app.utils.sliding_window_util import SlidingWindowUtil
from app.schemas.equity_schema import ConstituentStockResponse
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


@equity_router.get(
    "/get-constituent-stocks",
    response_model=ConstituentStockResponse
)
def get_constituent_stocks(
    parent_equity_id: int,
    db: Session = Depends(get_db)
):
    equities = EquityRepository.get_constituent_stocks(db, parent_equity_id)
    return {"equities": equities, "success": True, "message": "Constituent stocks fetched successfully"}

# =========== Anomaly Trading ================

@equity_router.get(
    "/backtrack-sectoral-anomaly",
)
def backtrack_sectoral_anomaly(
    sector_id: int,
    db: Session = Depends(get_db),
):
    equity = EquityRepository.get_equity_prices(db, sector_id)
    if not equity:
        return {"message": "Equity not found", "success": False}
    print("===============================================\n")
    print(equity[0])
    print("===============================================\n")

    sw = SlidingWindowUtil(data=equity)
    data = sw.scan_sector()
    return JSONResponse(
        status_code=200,
        content={"success": True, "message": "Done", "data": data}
    )


# ===========================================-


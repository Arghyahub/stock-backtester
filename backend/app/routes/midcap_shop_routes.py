from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependecies import get_current_user
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.midcap_shop_schema import RecordMidcapShopTradeRequest
from app.services.midcap_shop_portfolio_service import portfolio, record_trade
from app.services.midcap_shop_service import scan

router = APIRouter(prefix="/midcap-shop", tags=["Midcap SHOP"])


@router.get("/scan")
def midcap_shop_scan():
    try:
        return scan()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Midcap SHOP scan is temporarily unavailable") from exc


@router.get("/portfolio")
def midcap_shop_portfolio(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return portfolio(db, user)


@router.post("/trades")
def save_midcap_shop_trade(
    data: RecordMidcapShopTradeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return record_trade(db, user, data)

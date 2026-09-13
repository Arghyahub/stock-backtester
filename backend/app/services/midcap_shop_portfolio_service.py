"""Authenticated, compact Midcap SHOP trade journal and signal evaluation."""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.midcap_shop import MidcapShopPosition, MidcapShopTradeEvent
from app.db.models.user import User
from app.schemas.midcap_shop_schema import RecordMidcapShopTradeRequest
from app.services.midcap_shop_service import scan


def _positions(db: Session, user_id: int) -> list[MidcapShopPosition]:
    return db.query(MidcapShopPosition).filter(MidcapShopPosition.user_id == user_id).order_by(MidcapShopPosition.ticker).all()


def _signals(positions: list[MidcapShopPosition], daily_scan: dict) -> dict:
    candidates = daily_scan["candidates"]
    by_ticker = {candidate["ticker"]: candidate for candidate in candidates}
    by_position = {position.ticker: position for position in positions}
    sell_tickers = sorted(
        position.ticker for position in positions
        if position.ticker in by_ticker and by_ticker[position.ticker]["close"] >= position.average_cost * 1.08
    )
    all_shortlisted_held = bool(candidates) and all(candidate["ticker"] in by_position for candidate in candidates)
    average_options = []
    if all_shortlisted_held:
        for candidate in candidates:
            position = by_position[candidate["ticker"]]
            decline = candidate["close"] / position.latest_purchase_price - 1
            if position.purchase_count < 4 and decline < -0.03:
                average_options.append((decline, position.ticker))
    average_options.sort()
    fresh = next((candidate["ticker"] for candidate in candidates if candidate["ticker"] not in by_position), None)
    if sell_tickers:
        action = {"type": "sell", "ticker": sell_tickers[0]}
    elif average_options:
        action = {"type": "average", "ticker": average_options[0][1]}
    elif fresh:
        action = {"type": "buy", "ticker": fresh}
    else:
        action = {"type": "none", "ticker": None}
    return {"action": action, "sell_tickers": sell_tickers, "average_ticker": average_options[0][1] if average_options else None,
            "fresh_ticker": fresh, "all_shortlisted_held": all_shortlisted_held, "candidate_by_ticker": by_ticker}


def _serialize_position(position: MidcapShopPosition, candidate: dict | None) -> dict:
    close = candidate["close"] if candidate else None
    return {"ticker": position.ticker, "quantity": position.quantity, "average_cost": position.average_cost,
            "latest_purchase_price": position.latest_purchase_price, "latest_purchase_date": str(position.latest_purchase_date),
            "purchase_count": position.purchase_count, "close": close, "value": round(position.quantity * close, 2) if close is not None else None,
            "target_price": round(position.average_cost * 1.08, 2)}


def portfolio(db: Session, user: User) -> dict:
    positions = _positions(db, user.pk_user_id)
    daily_scan = scan()
    signal = _signals(positions, daily_scan)
    events = db.query(MidcapShopTradeEvent).filter(MidcapShopTradeEvent.user_id == user.pk_user_id).order_by(
        MidcapShopTradeEvent.execution_date.desc(), MidcapShopTradeEvent.pk_midcap_shop_trade_event_id.desc()).limit(100).all()
    return {"positions": [_serialize_position(item, signal["candidate_by_ticker"].get(item.ticker)) for item in positions],
            "signal": {key: value for key, value in signal.items() if key != "candidate_by_ticker"},
            "history": [{"id": event.pk_midcap_shop_trade_event_id, "ticker": event.ticker, "action": event.action,
                         "quantity": event.quantity, "execution_price": event.execution_price, "execution_date": str(event.execution_date),
                         "cost_basis": event.cost_basis, "realized_pnl": event.realized_pnl} for event in events]}


def record_trade(db: Session, user: User, data: RecordMidcapShopTradeRequest) -> dict:
    ticker = data.ticker.strip().upper()
    positions = _positions(db, user.pk_user_id)
    position_by_ticker = {position.ticker: position for position in positions}
    daily_scan = scan()
    signal = _signals(positions, daily_scan)
    expected = signal["action"]
    eligible = ticker in signal["sell_tickers"] if data.action == "sell" else expected["type"] == data.action and expected["ticker"] == ticker
    if not eligible:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This trade is not the current eligible Midcap SHOP action")
    if data.action in {"buy", "average"}:
        existing_purchase = db.query(MidcapShopTradeEvent).filter(
            MidcapShopTradeEvent.user_id == user.pk_user_id,
            MidcapShopTradeEvent.execution_date == data.execution_date,
            MidcapShopTradeEvent.action.in_(["buy", "average"]),
        ).first()
        if existing_purchase:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only one Midcap SHOP purchase may be recorded per day")
        if data.quantity is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Quantity is required for a purchase")
        now = datetime.now(timezone.utc)
        if data.action == "buy":
            position = MidcapShopPosition(user_id=user.pk_user_id, ticker=ticker, quantity=data.quantity,
                                          average_cost=data.execution_price, latest_purchase_price=data.execution_price,
                                          latest_purchase_date=data.execution_date, purchase_count=1, opened_at=now, updated_at=now)
            db.add(position)
        else:
            position = position_by_ticker[ticker]
            total_quantity = position.quantity + data.quantity
            position.average_cost = (position.average_cost * position.quantity + data.execution_price * data.quantity) / total_quantity
            position.quantity = total_quantity
            position.latest_purchase_price = data.execution_price
            position.latest_purchase_date = data.execution_date
            position.purchase_count += 1
            position.updated_at = now
        db.add(MidcapShopTradeEvent(user_id=user.pk_user_id, ticker=ticker, action=data.action, quantity=data.quantity,
                                    execution_price=data.execution_price, execution_date=data.execution_date, cost_basis=None,
                                    realized_pnl=None, created_at=now))
    else:
        position = position_by_ticker[ticker]
        if data.quantity is not None and data.quantity != position.quantity:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A Midcap SHOP sell closes the entire saved position")
        now = datetime.now(timezone.utc)
        cost_basis = position.quantity * position.average_cost
        proceeds = position.quantity * data.execution_price
        db.add(MidcapShopTradeEvent(user_id=user.pk_user_id, ticker=ticker, action="sell", quantity=position.quantity,
                                    execution_price=data.execution_price, execution_date=data.execution_date, cost_basis=cost_basis,
                                    realized_pnl=proceeds - cost_basis, created_at=now))
        db.delete(position)
    db.commit()
    return portfolio(db, user)

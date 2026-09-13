from datetime import date, datetime

from app.db.models.midcap_shop import MidcapShopPosition
from app.services.midcap_shop_portfolio_service import _signals


def position(ticker: str, average: float, latest: float, purchases: int = 1) -> MidcapShopPosition:
    return MidcapShopPosition(
        user_id=1, ticker=ticker, quantity=10, average_cost=average,
        latest_purchase_price=latest, latest_purchase_date=date(2026, 9, 10),
        purchase_count=purchases, opened_at=datetime.now(), updated_at=datetime.now(),
    )


def daily_scan(closes: dict[str, float]) -> dict:
    return {"candidates": [{"ticker": ticker, "close": close, "shortlist_rank": rank}
                           for rank, (ticker, close) in enumerate(closes.items(), start=1)]}


def test_sell_signal_takes_priority_over_average_and_fresh():
    result = _signals([position("A", 100, 100)], daily_scan({"A": 108, "B": 90, "C": 90, "D": 90, "E": 90}))
    assert result["sell_tickers"] == ["A"]
    assert result["action"] == {"type": "sell", "ticker": "A"}


def test_average_requires_all_shortlisted_and_selects_largest_decline():
    positions = [position(ticker, 100, latest) for ticker, latest in {"A": 100, "B": 100, "C": 100, "D": 100, "E": 100}.items()]
    result = _signals(positions, daily_scan({"A": 96, "B": 92, "C": 97, "D": 98, "E": 99}))
    assert result["all_shortlisted_held"] is True
    assert result["average_ticker"] == "B"
    assert result["action"] == {"type": "average", "ticker": "B"}


def test_purchase_cap_disables_average_and_keeps_fresh_signal():
    positions = [position("A", 100, 100, purchases=4)]
    result = _signals(positions, daily_scan({"A": 90, "B": 90, "C": 90, "D": 90, "E": 90}))
    assert result["average_ticker"] is None
    assert result["action"] == {"type": "buy", "ticker": "B"}

from datetime import date

import pandas as pd
import pytest

from app.services import midcap_shop_service as service


def frame(values):
    return pd.DataFrame({"Close": values}, index=pd.bdate_range("2026-08-01", periods=len(values)))


def test_build_scan_ranks_lowest_distance_and_uses_completed_session(monkeypatch):
    universe = {f"S{i}.NS": f"Stock {i}" for i in range(5)}
    monkeypatch.setattr(service, "fetch_universe", lambda: universe)
    monkeypatch.setattr(service, "fetch_prices", lambda *_: {
        ticker: frame([100.0] * 20 + [100.0 - i]) for i, ticker in enumerate(universe)
    })
    result = service.build_scan(date(2026, 9, 13))
    assert [item["ticker"] for item in result["candidates"]] == ["S4.NS", "S3.NS", "S2.NS", "S1.NS", "S0.NS"]
    assert result["candidates"][0]["shortlist_rank"] == 1
    assert result["as_of_date"] == "2026-08-31"


def test_cache_returns_stale_last_success_after_provider_failure(monkeypatch):
    service.clear_cache()
    fresh = {"as_of_date": "2026-09-11", "generated_at": "now", "stale": False, "universe_size": 50, "candidates": []}
    monkeypatch.setattr(service, "build_scan", lambda: fresh)
    assert service.scan()["stale"] is False
    monkeypatch.setattr(service, "build_scan", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    # Expire the cache without sleeping.
    service._cache_at = service._cache_at.replace(year=2000)
    assert service.scan()["stale"] is True


def test_no_cached_failure_is_raised(monkeypatch):
    service.clear_cache()
    monkeypatch.setattr(service, "build_scan", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    with pytest.raises(RuntimeError, match="offline"):
        service.scan()

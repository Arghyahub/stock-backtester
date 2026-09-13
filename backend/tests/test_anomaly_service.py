import os
from types import SimpleNamespace

import pandas as pd

os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("JWT_SECRET", "test")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "30")

from app.services.anomaly_service import first_session, instrument_metric


def test_first_session_moves_weekend_to_next_session():
    sessions = pd.DatetimeIndex(["2025-03-07", "2025-03-10", "2025-03-11"])
    assert first_session(sessions, 2025, 3, 8) == 1


def test_instrument_metrics_pool_same_seasonal_window_across_years():
    index = pd.to_datetime(["2021-01-04", "2021-01-05", "2021-01-06", "2022-01-03", "2022-01-04", "2022-01-05"])
    benchmark = pd.Series([100, 101, 102, 100, 101, 102], index=index, dtype=float)
    asset = pd.Series([100, 102, 104, 100, 102, 104], index=index, dtype=float)
    plan = SimpleNamespace(month=1, day=1, window_days=2)
    metric = instrument_metric(benchmark, asset, plan, [2021, 2022])
    assert metric is not None
    seasonal_return, alpha, beta, observations, _ = metric
    assert seasonal_return > 0
    assert beta > 1
    assert observations == 4

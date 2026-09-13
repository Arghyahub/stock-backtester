"""Research settings. Change deliberately and record any change in your results."""

from datetime import date

SECTORS = {
    "Nifty IT": "^CNXIT",
    "Nifty Bank": "^NSEBANK",
    "Nifty Auto": "^CNXAUTO",
    "Nifty FMCG": "^CNXFMCG",
    "Nifty Pharma": "^CNXPHARMA",
    "Nifty Metal": "^CNXMETAL",
    "Nifty Realty": "^CNXREALTY",
    "Nifty Energy": "^CNXENERGY",
    "Nifty Financial Services": "NIFTY_FIN_SERVICE.NS",
    "Nifty Media": "^CNXMEDIA",
}

MIN_WINDOW_DAYS = 1
MAX_WINDOW_DAYS = 60
COMPLETED_YEARS = 5
MIN_TRAIN_OBSERVATIONS = 3
MIN_TRAIN_WIN_RATE = 0.60
MIN_TRAIN_MEAN_RETURN = 0.0
MAX_TRAIN_DRAWDOWN = -0.10
ROUND_TRIP_COST = 0.0020  # 20 bps, deducted from each completed trade
TOP_PLANS = 20

# Final out-of-sample report filters. A drawdown is naturally negative; only
# losses beyond this downside limit are rejected.
MIN_OOS_WIN_RATE = 1.00       # both OOS years must be positive in this 5-year setup
MIN_OOS_WORST_RETURN = 0.03   # every OOS trade must return more than 3%
MAX_OOS_DRAWDOWN = -0.10      # reject a drawdown worse than -10%


def completed_years(today: date | None = None) -> list[int]:
    """Return a fixed five-year, fully completed calendar-year sample."""
    current = (today or date.today()).year
    return list(range(current - COMPLETED_YEARS, current))

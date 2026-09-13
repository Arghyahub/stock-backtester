"""Fixed settings for the daily Nifty 200 CMF study."""

from datetime import date

COMPLETED_YEARS = 5
CMF_LENGTH = 40
CMF_THRESHOLD = 0.05
EMA_LENGTH = 200
FAST_EMA_LENGTH = 50
RSI_LENGTH = 14
RSI_MIN = 50.0
RSI_MAX = 70.0
ATR_LENGTH = 14
STOP_ATR_MULTIPLIER = 2.0
RISK_REWARD_RATIO = 2.0
ROUND_TRIP_COST = 0.0020  # 20 bps deducted from every completed/marked trade
NIFTY200_CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv"


def completed_years(today: date | None = None) -> list[int]:
    """Return the latest five full calendar years, excluding the current year."""
    current = (today or date.today()).year
    return list(range(current - COMPLETED_YEARS, current))

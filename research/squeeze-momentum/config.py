"""Pre-committed settings for the daily NSE Squeeze Momentum study."""

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

COMPLETED_YEARS = 5
BB_LENGTH = 20
BB_MULTIPLIER = 2.0
KC_LENGTH = 20
KC_MULTIPLIER = 1.5
EMA_LENGTH = 200
ATR_LENGTH = 14
MIN_SQUEEZE_DAYS = 6
STOP_ATR_MULTIPLIER = 2.0
ROUND_TRIP_COST = 0.0020  # 20 bps deducted from each completed trade

# Objective versions of the video's discretionary checks. They are deliberately
# reported as separate variants, not optimised after examining the outcome.
RANGE_LOOKBACK = 20
MAX_RANGE_ATR_MULTIPLE = 8.0
EXPANSION_LOOKBACK = 20
MAX_TRUE_RANGE_MEDIAN_MULTIPLE = 2.5

# Exploratory daily-OHLCV improvement, sourced from documented TTM/Squeeze
# practice. These values are fixed before this Nifty 200 run.
ADX_LENGTH = 14
MIN_ADX = 20.0
VOLUME_LOOKBACK = 20
MIN_RELATIVE_VOLUME = 1.20
FAST_EMA_LENGTH = 50
TRAILING_STOP_ATR_MULTIPLIER = 2.0
NIFTY200_CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv"


def completed_years(today: date | None = None) -> list[int]:
    """Return the latest five full calendar years, excluding the current year."""
    current = (today or date.today()).year
    return list(range(current - COMPLETED_YEARS, current))

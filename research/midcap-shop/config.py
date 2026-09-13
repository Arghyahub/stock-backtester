"""Fixed settings for the cost-aware Nifty Midcap SHOP study."""

from datetime import date

INITIAL_CASH = 100_000.0
SMA_LENGTH = 20
SHORTLIST_SIZE = 5
FRESH_DIVISOR = 10
AVERAGE_DIVISOR = 40
AVERAGE_TRIGGER = 0.03
MAX_AVERAGE_BUYS_PER_STOCK = 3
TARGET_RETURN = 0.08
RSI_LENGTH = 14
RSI_OVERSOLD = 30.0
TREND_SMA_LENGTH = 200
COMPLETED_YEARS = 5
NIFTY_MIDCAP_50_CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap50list.csv"

# Current retail individual CNC delivery schedule, applied to every historical trade.
STT_RATE = 0.001
NSE_TRANSACTION_RATE = 0.0000307
SEBI_RATE = 10 / 10_000_000
GST_RATE = 0.18
STAMP_BUY_RATE = 0.00015
DP_SELL_PER_SCRIP_DAY = 15.34


def completed_years(today: date | None = None) -> list[int]:
    current = (today or date.today()).year
    return list(range(current - COMPLETED_YEARS, current))

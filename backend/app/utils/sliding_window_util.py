from app.schemas.equity_schema import YFinanceModel
from app.db.models import Price
import pandas as pd
import numpy as np

class SlidingWindowUtil:
    def __init__(self,data:list[YFinanceModel], MIN_WINDOW: int = 1, MAX_WINDOW: int = 60, MIN_OBSERVATIONS: int = 4, MIN_WIN_RATE: float = 65.0, MIN_AVG_RETURN: float = 3.0, MIN_SHARPE: float = 0.8, MAX_DRAWDOWN: float = -5.0):
        self.MIN_WINDOW = MIN_WINDOW
        self.MAX_WINDOW = MAX_WINDOW
        self.MIN_OBSERVATIONS = MIN_OBSERVATIONS
        df = pd.DataFrame(data)
        df = df.sort_values(by='Date')
        df = df.set_index('Date')
        self.df = df
        # Filters
        self.MIN_WIN_RATE = MIN_WIN_RATE
        self.MIN_AVG_RETURN = MIN_AVG_RETURN
        self.MIN_SHARPE = MIN_SHARPE
        self.MAX_DRAWDOWN = MAX_DRAWDOWN

    # ── Helper Functions ──────────────────────────────────────────────────────────

    # def load_sector(sector_name):
    #     """
    #     Load a sector CSV from disk.
    #     Returns a DataFrame with DatetimeIndex and a 'Close' column.
    #     """
    #     filename = sector_name.replace(' ', '_').lower() + '.csv'
    #     filepath = os.path.join(RAW_DATA_DIR, filename)
    #     df = pd.read_csv(filepath, index_col='Date', parse_dates=True)
    #     df = df.sort_index()
    #     return df[['Close']]


    def get_window_return(self,close_series, start_idx, window_size):
        """
        Given a Close price series and a starting position index,
        return the % return over the next `window_size` trading days.
        Returns None if there aren't enough days.
        """
        end_idx = start_idx + window_size
        if end_idx >= len(close_series):
            return None
        
        price_start = close_series.iloc[start_idx]
        price_end   = close_series.iloc[end_idx]
        
        if price_start == 0 or pd.isna(price_start) or pd.isna(price_end):
            return None
        
        return (price_end - price_start) / price_start * 100  # % return


    def get_max_drawdown(self,close_series, start_idx, window_size):
        """
        Compute the maximum intra-window drawdown (%) from the entry price.
        This measures how far the price drops below entry at any point in the window.
        Returns None if data is insufficient.
        """
        end_idx = start_idx + window_size
        if end_idx >= len(close_series):
            return None
        
        window_prices = close_series.iloc[start_idx:end_idx + 1]
        entry_price   = window_prices.iloc[0]
        
        if entry_price == 0 or pd.isna(entry_price):
            return None
        
        # Drawdown = worst % drop below entry during the window
        min_price = window_prices.min()
        drawdown  = (min_price - entry_price) / entry_price * 100  # negative number
        return drawdown


    def compute_metrics(self,returns_list, drawdowns_list):
        """
        Given a list of returns (one per historical year) and drawdowns,
        compute the 4 core metrics.
        """
        returns   = np.array([r for r in returns_list if r is not None])
        drawdowns = np.array([d for d in drawdowns_list if d is not None])
        
        if len(returns) < self.MIN_OBSERVATIONS:
            return None  # Not enough data points to trust
        
        avg_return   = np.mean(returns)
        win_rate     = np.sum(returns > 0) / len(returns) * 100  # % of years positive
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else np.nan  # worst drawdown
        
        # Sharpe: avg return / std of returns
        # (We skip risk-free rate since windows are short; relative Sharpe is what matters)
        std = np.std(returns, ddof=1)
        sharpe = avg_return / std if std > 0 else 0.0
        
        return {
            'avg_return'   : round(avg_return, 4),
            'win_rate'     : round(win_rate, 2),
            'max_drawdown' : round(max_drawdown, 4),
            'sharpe'       : round(sharpe, 4),
            'n_obs'        : len(returns),   # how many years contributed
        }
    
    # ── Core Scanning Logic ───────────────────────────────────────────────────────
    #
    # How the sliding window works:
    #
    # For a given (sector, window_size, calendar_day):
    #   → Find every occurrence of that calendar day in the price history
    #   → For each occurrence, measure the return over the next `window_size` trading days
    #   → Collect all those returns → compute metrics
    #
    # Calendar day is represented as (month, day) — e.g. (10, 1) = Oct 1
    # We find the nearest trading day on or after that calendar date each year.
    #
    # This handles weekends/holidays: if Oct 1 is a Sunday, we use Oct 2 (Monday).

    def find_nearest_trading_day(self,df_index, year, month, day):
        """
        Given a DatetimeIndex (trading days only), find the first trading day
        on or after the target (year, month, day).
        Returns the integer position in df_index, or None if not found.
        """
        try:
            target = pd.Timestamp(year=year, month=month, day=day)
        except ValueError:
            # Invalid date like Feb 30 — skip
            return None
        
        # Find trading days >= target within the same year
        candidates = df_index[(df_index >= target) & (df_index.year == year)]
        
        if len(candidates) == 0:
            return None
        
        nearest = candidates[0]
        return df_index.get_loc(nearest)
    
    # Normalize each metric to 0-1 scale within the filtered set
    def minmax(self,series):
        mn, mx = series.min(), series.max()
        if mx == mn:
            return pd.Series(0.5, index=series.index)
        return (series - mn) / (mx - mn)

    def apply_ranking(self, results):
        if not results:
            return []

        df = pd.DataFrame(results)

        df = df[
            (df['win_rate']     >= self.MIN_WIN_RATE)     &
            (df['avg_return']   >= self.MIN_AVG_RETURN)   &
            (df['sharpe']       >= self.MIN_SHARPE)       &
            (df['max_drawdown'] >= self.MAX_DRAWDOWN)     &
            (df['n_obs']        >= (self.MIN_OBSERVATIONS -1))
        ].copy()

        if len(df) == 0:
            return []

        df['score_return'] = self.minmax(df['avg_return'])
        df['score_winrate'] = self.minmax(df['win_rate'])
        df['score_sharpe'] = self.minmax(df['sharpe'])
        df['score_drawdown'] = self.minmax(df['max_drawdown'])

        df['composite_score'] = (
            df['score_sharpe'] * 0.35 +
            df['score_winrate'] * 0.30 +
            df['score_return'] * 0.25 +
            df['score_drawdown'] * 0.10
        ).round(4)

        return (
            df.sort_values("composite_score", ascending=False)
            .to_dict("records")
        )


    def scan_sector(self):
        df = self.df[['Close']]
        """
        Run the full sliding window scan for one sector.
        Returns a list of result dicts — one per (window_size, month, day) combo.
        """
        close  = df['Close']
        index  = df.index
        years  = sorted(index.year.unique())
        results = []
        
        # Iterate over every (month, day) combination in the calendar year
        # We'll use 2000 as a reference leap year to get all 366 possible dates
        all_calendar_days = pd.date_range('2000-01-01', '2000-12-31', freq='D')
        
        for window_size in range(self.MIN_WINDOW, self.MAX_WINDOW + 1):
            for cal_date in all_calendar_days:
                month = cal_date.month
                day   = cal_date.day
                
                returns_list   = []
                drawdowns_list = []
                
                for year in years:
                    # Find the nearest trading day for this calendar date in this year
                    pos = self.find_nearest_trading_day(index, year, month, day)
                    if pos is None:
                        continue
                    
                    ret = self.get_window_return(close, pos, window_size)
                    dd  = self.get_max_drawdown(close, pos, window_size)
                    
                    if ret is not None:
                        returns_list.append(ret)
                    if dd is not None:
                        drawdowns_list.append(dd)
                
                # Compute metrics for this (window_size, month, day) combo
                metrics = self.compute_metrics(returns_list, drawdowns_list)
                
                if metrics is None:
                    continue  # Not enough observations
                
                results.append({
                    # 'sector'      : sector_name,
                    'month'       : month,
                    'day'         : day,
                    'start_label' : f"{cal_date.strftime('%b')} {day:02d}",  # e.g. 'Oct 01'
                    'window_days' : window_size,
                    'end_label'   : (cal_date + pd.Timedelta(days=window_size)).strftime('%b %d'),
                    **metrics
                })
        
        return self.apply_ranking(results)

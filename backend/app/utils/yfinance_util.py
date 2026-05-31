import yfinance as yf
import pandas as pd

class YFinanceUtil:
    @staticmethod
    def download_sector_data(ticker: str, start_date: str, end_date: str):    
        try:
            # Download OHLCV data
            raw = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,   # suppress yfinance progress bar
                auto_adjust=True  # adjusts for splits/dividends automatically
            )
            
            # ── Validate ──────────────────────────────────────────────────────────
            if raw.empty:
                print(f'  ⚠ No data returned for {ticker}. Skipping.')
                return ({
                    'Ticker'      : ticker,
                    'Status'      : 'FAILED — no data',
                    'Start Date'  : None,
                    'End Date'    : None,
                    'Total Days'  : 0,
                    'Years Approx': 0,
                    'Missing %'   : None,
                    'Data': None
                })
            
            # Flatten multi-level columns if present (yfinance sometimes returns them)
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            
            # Keep only relevant columns
            df = raw[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df.index.name = 'Date'
            
            # ── Check for missing values ───────────────────────────────────────────
            missing_count = df['Close'].isna().sum()
            missing_pct   = round(missing_count / len(df) * 100, 2)
            
            # Forward-fill small gaps (holidays, etc.) — max 3 consecutive days
            df = df.ffill(limit=3)
            
            # Drop any remaining NaNs
            df = df.dropna()
            
            actual_start = df.index.min().strftime('%Y-%m-%d')
            actual_end   = df.index.max().strftime('%Y-%m-%d')
            years_approx = round(len(df) / 252, 1)  # ~252 trading days per year
            
            print(f'  ✓ {len(df)} trading days | {actual_start} → {actual_end} | ~{years_approx} yrs | Missing: {missing_pct}%')
            
            return ({
                'Ticker'      : ticker,
                'Status'      : 'OK',
                'Start Date'  : actual_start,
                'End Date'    : actual_end,
                'Total Days'  : len(df),
                'Years Approx': years_approx,
                'Missing %'   : missing_pct,
                'Data': df.reset_index().to_dict(orient='records')
            })
        
        except Exception as e:
            print(f'  ✗ Error fetching {ticker}: {e}')
            return ({
                'Ticker'      : ticker,
                'Status'      : f'ERROR — {str(e)}',
                'Start Date'  : None,
                'End Date'    : None,
                'Total Days'  : 0,
                'Years Approx': 0,
                'Missing %'   : None,
                'Data': None
            })
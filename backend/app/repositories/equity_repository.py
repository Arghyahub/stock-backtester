from app.schemas.equity_schema import EquitySummary
from app.schemas.equity_schema import TrackEquityBase
from app.utils.yfinance_util import YFinanceUtil
from datetime import datetime
from typing import TypedDict
from sqlalchemy import text
from app.schemas.equity_schema import TrackEquityRequest
from sqlalchemy.orm import Session
from datetime import date

from app.db.models.equity import Equity
from app.db.models.price import Price
from app.utils.yfinance_util import YFinanceUtil

class EquityWithDate(TypedDict):
    equity_id: int
    name: str
    ticker: str
    start_date: datetime
    end_date: datetime


class EquityRepository:

    @staticmethod
    def create_and_track_equities(
        db: Session,
        data: TrackEquityRequest
    ):
        tickers = [equity.ticker for equity in data.equities]

        qry = text("""
            SELECT 
                e.pk_equity_id as equity_id,
                e.name,
                e.ticker,
                first_price.date_time as start_date,
                last_price.date_time as end_date
            FROM "equities" e
            left join lateral(
                select 
                    p.date_time
                from "prices" p 
                where p.equity_id = e.pk_equity_id 
                and p.interval = 'ONE_DAY'
                order by p.date_time asc limit 1
            ) first_price on TRUE
            left join lateral(
                select 
                    p.date_time 
                from "prices" p 
                where p.equity_id = e.pk_equity_id 
                and p.interval = 'ONE_DAY'
                order by p.date_time desc limit 1
            ) last_price on TRUE
            WHERE e.ticker = ANY(:tickers)
            and e.type  = :equity_type
            ;
        """)

        result:list[EquityWithDate] = db.execute(qry, {"tickers": tickers, "equity_type": data.type.value}).all()

        equity_not_exists:list[TrackEquityBase] = []
        existing_equities: dict[str, EquityWithDate] = {equity.ticker: equity for equity in result}

        for equity in data.equities:
            if equity.ticker not in existing_equities:
                equity_not_exists.append(equity)
        
        if len(equity_not_exists) > 0:
            equities = [Equity(ticker=equity.ticker, name=equity.name, type=data.type.value) for equity in equity_not_exists]
            db.add_all(equities)
            db.commit()
        
        # Check start_date and end_date exists or not else add to equity_not_exists
        for eq in data.equities:
            if eq.ticker in existing_equities:
                if existing_equities[eq.ticker].start_date is None or existing_equities[eq.ticker].end_date is None:
                    equity_not_exists.append(eq)
        
        # Pull data from yfinance from 6 years ago start of year to last year's end of year
        today = date.today()

        start_date = date(today.year - 6, 1, 1)
        end_date = date(today.year - 1, 12, 31)

        all_equities = db.query(Equity).filter(Equity.ticker.in_(tickers)).all()
        ticker_to_id = {eq.ticker: eq.pk_equity_id for eq in all_equities}

        new_prices = []
        for equity in equity_not_exists:
            equity_id = ticker_to_id.get(equity.ticker)
            if not equity_id:
                continue

            res = YFinanceUtil.download_sector_data(
                ticker=equity.ticker,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )

            if res.get('Status') == 'OK' and res.get('Data'):
                for row in res['Data']:
                    new_prices.append(
                        Price(
                            equity_id=equity_id,
                            date_time=row['Date'],
                            interval=data.interval.value,
                            open=row['Open'],
                            high=row['High'],
                            low=row['Low'],
                            close=row['Close'],
                            volume=row['Volume'],
                            dividends=0.0,
                            stock_splits=0.0,
                            trades_count=0
                        )
                    )

        if new_prices:
            db.add_all(new_prices)
            db.commit()
        
    @staticmethod
    def get_equity_summary(db: Session, type: str):
        qry = text("""
            SELECT 
                e.pk_equity_id as equity_id,
                e.name,
                e.ticker,
                first_price.date_time as start_date,
                last_price.date_time as end_date,
                signal_count.signal_count
            FROM "equities" e
            left join lateral(
                select 
                    p.date_time
                from "prices" p 
                where p.equity_id = e.pk_equity_id 
                and p.interval = 'ONE_DAY'
                order by p.date_time asc limit 1
            ) first_price on TRUE
            left join lateral(
                select 
                    p.date_time 
                from "prices" p 
                where p.equity_id = e.pk_equity_id 
                and p.interval = 'ONE_DAY'
                order by p.date_time desc limit 1
            ) last_price on TRUE
            left join lateral(
                select 
                    count(*) as signal_count
                from "trades" t 
                where t.equity_id = e.pk_equity_id
            ) signal_count on TRUE
            WHERE e.type  = :type
            ;
        """)

        result = db.execute(qry, {"type": type}).all()
        return [dict(row._mapping) for row in result]
            
        
        


from datetime import date, timedelta
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.dependecies import get_current_admin
from app.db.database import SessionLocal, get_db
from app.db.enums import EquityType
from app.db.models.anomaly import InstrumentMapping, PlanInstrument, StrategyPlan, StrategyRun
from app.db.models.equity import Equity
from app.db.models.strategy import Strategy
from app.schemas.anomaly_schema import Headline, MappingRequest, MappingResponse, PlanSummary
from app.services.anomaly_service import compute, headlines, live_plan_instruments, refresh_mapped_data, track_sector_instruments

router = APIRouter(prefix="/anomaly", tags=["Anomaly Trading V2"])


def strategy(db: Session) -> Strategy:
    item = db.query(Strategy).filter(Strategy.key == "anomaly-trading").first()
    if not item: raise HTTPException(404, "Create the Anomaly Trading strategy in admin first")
    return item


def plan_response(db: Session, plan: StrategyPlan) -> dict:
    sector = db.get(Equity, plan.sector_equity_id)
    selected = db.query(PlanInstrument, Equity).join(Equity, Equity.pk_equity_id == PlanInstrument.equity_id).filter(PlanInstrument.strategy_plan_id == plan.pk_strategy_plan_id, PlanInstrument.is_recommended.is_(True)).all()
    instruments = {x.instrument_type: {"ticker": e.ticker, "name": e.name, "instrument_type": x.instrument_type,
                   "seasonal_return": x.seasonal_return, "alpha": x.alpha, "beta": x.beta, "observation_count": x.observation_count} for x, e in selected}
    entry = date(date.today().year, plan.month, plan.day)
    return {"plan_id": plan.pk_strategy_plan_id, "sector": sector.name, "entry_date": entry.isoformat(),
            "exit_date": (entry + timedelta(days=plan.window_days)).isoformat(), "window_days": plan.window_days,
            "oos_mean_return": plan.oos_mean_return, "oos_win_rate": plan.oos_win_rate, "oos_worst_return": plan.oos_worst_return,
            "oos_worst_drawdown": plan.oos_worst_drawdown, "stock": instruments.get("STOCK"), "etf": instruments.get("ETF")}


def serialized_plan(row: tuple) -> dict:
    plan, sector, stock_metric, stock, etf_metric, etf = row
    def instrument(metric: PlanInstrument | None, equity: Equity | None):
        if not metric or not equity: return None
        return {"ticker": equity.ticker, "name": equity.name, "instrument_type": metric.instrument_type,
                "seasonal_return": metric.seasonal_return, "alpha": metric.alpha, "beta": metric.beta,
                "observation_count": metric.observation_count}
    entry = date(date.today().year, plan.month, plan.day)
    return {"plan_id": plan.pk_strategy_plan_id, "sector": sector.name, "entry_date": entry.isoformat(),
            "exit_date": (entry + timedelta(days=plan.window_days)).isoformat(), "window_days": plan.window_days,
            "oos_mean_return": plan.oos_mean_return, "oos_win_rate": plan.oos_win_rate,
            "oos_worst_return": plan.oos_worst_return, "oos_worst_drawdown": plan.oos_worst_drawdown,
            "stock": instrument(stock_metric, stock), "etf": instrument(etf_metric, etf)}


def published_plan_query(run_id: int, start: date | None = None, end: date | None = None, sort: str = "date"):
    stock_metric, etf_metric = aliased(PlanInstrument), aliased(PlanInstrument)
    stock, etf = aliased(Equity), aliased(Equity)
    entry = func.make_date(date.today().year, StrategyPlan.month, StrategyPlan.day)
    statement = (
        select(StrategyPlan, Equity, stock_metric, stock, etf_metric, etf)
        .join(Equity, Equity.pk_equity_id == StrategyPlan.sector_equity_id)
        .outerjoin(stock_metric, (stock_metric.strategy_plan_id == StrategyPlan.pk_strategy_plan_id) & (stock_metric.instrument_type == "STOCK") & stock_metric.is_recommended.is_(True))
        .outerjoin(stock, stock.pk_equity_id == stock_metric.equity_id)
        .outerjoin(etf_metric, (etf_metric.strategy_plan_id == StrategyPlan.pk_strategy_plan_id) & (etf_metric.instrument_type == "ETF") & etf_metric.is_recommended.is_(True))
        .outerjoin(etf, etf.pk_equity_id == etf_metric.equity_id)
        .where(StrategyPlan.strategy_run_id == run_id)
    )
    if start and end:
        statement = statement.where(entry.between(start, end))
        ordering = entry if sort == "date" else StrategyPlan.oos_worst_return.desc() if sort == "worst" else StrategyPlan.oos_mean_return.desc()
        statement = statement.order_by(ordering, entry)
    return statement


@router.get("/upcoming", response_model=list[PlanSummary])
def upcoming(days: int = 30, db: Session = Depends(get_db)):
    if not 1 <= days <= 365: raise HTTPException(422, "days must be between 1 and 365")
    latest = db.query(StrategyRun).join(Strategy).filter(Strategy.key == "anomaly-trading").order_by(StrategyRun.computed_at.desc()).first()
    if not latest: return []
    today, end = date.today(), date.today() + timedelta(days=days)
    return [serialized_plan(row) for row in db.execute(published_plan_query(latest.pk_strategy_run_id, today, end)).all()]


@router.get("/calendar")
def calendar(days: int = 365, view: str = "calendar", start_date: date | None = None, end_date: date | None = None, page: int = 1, page_size: int = 24, sort: str = "date", db: Session = Depends(get_db)):
    if not 1 <= days <= 365 or not 1 <= page or not 1 <= page_size <= 100 or sort not in {"date", "average", "worst"} or view not in {"calendar", "upcoming", "active", "completed", "custom"}:
        raise HTTPException(422, "Invalid calendar paging or sorting options")
    latest = db.query(StrategyRun).join(Strategy).filter(Strategy.key == "anomaly-trading").order_by(StrategyRun.computed_at.desc()).first()
    if not latest: return {"items": [], "total": 0, "page": page, "page_size": page_size}
    today = date.today()
    start, end = (date(today.year, 1, 1), date(today.year, 12, 31)) if view == "calendar" else (today, today + timedelta(days=days))
    if view == "custom":
        if not start_date or not end_date or start_date > end_date: raise HTTPException(422, "custom view requires a valid start_date and end_date")
        start, end = start_date, end_date
    entry = func.make_date(today.year, StrategyPlan.month, StrategyPlan.day)
    exit_date = entry + StrategyPlan.window_days
    condition = entry.between(start, end)
    if view == "upcoming": condition = entry.between(today, end)
    elif view == "active": condition = (entry <= today) & (exit_date >= today)
    elif view == "completed": condition = exit_date < today
    total = db.scalar(select(func.count()).select_from(StrategyPlan).where(StrategyPlan.strategy_run_id == latest.pk_strategy_run_id, condition)) or 0
    statement = published_plan_query(latest.pk_strategy_run_id, None, None, sort).where(condition)
    ordering = entry if sort == "date" else StrategyPlan.oos_worst_return.desc() if sort == "worst" else StrategyPlan.oos_mean_return.desc()
    rows = db.execute(statement.order_by(ordering, entry).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [serialized_plan(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/plans/{plan_id}", response_model=PlanSummary)
def detail(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(StrategyPlan, plan_id)
    if not plan: raise HTTPException(404, "Plan not found")
    return plan_response(db, plan)


@router.get("/plans/{plan_id}/headlines", response_model=list[Headline])
def plan_headlines(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(StrategyPlan, plan_id)
    if not plan: raise HTTPException(404, "Plan not found")
    sector = db.get(Equity, plan.sector_equity_id)
    return headlines(f"{sector.name} NSE")


@router.get("/plans/{plan_id}/instruments")
def plan_instruments(plan_id: int, db: Session = Depends(get_db)):
    """Live, non-persisted Yahoo Finance analysis for a single public detail card."""
    try:
        return {"instruments": live_plan_instruments(db, plan_id), "source": "Yahoo Finance", "stored": False}
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/admin/mappings", response_model=list[MappingResponse])
def mappings(_: object = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.query(InstrumentMapping, Equity).join(Equity, Equity.pk_equity_id == InstrumentMapping.instrument_equity_id).all()
    return [{"mapping_id": mapping.pk_instrument_mapping_id, "sector_equity_id": mapping.sector_equity_id,
             "instrument_equity_id": equity.pk_equity_id, "ticker": equity.ticker, "name": equity.name,
             "instrument_type": equity.type.value} for mapping, equity in rows]


@router.post("/admin/mappings", response_model=MappingResponse)
def create_mapping(data: MappingRequest, _: object = Depends(get_current_admin), db: Session = Depends(get_db)):
    sector = db.get(Equity, data.sector_equity_id)
    if not sector or sector.type != EquityType.SECTOR: raise HTTPException(422, "sector_equity_id must be a tracked sector")
    instrument = db.query(Equity).filter(Equity.ticker == data.ticker).first()
    if not instrument:
        instrument = Equity(ticker=data.ticker, name=data.name, type=EquityType(data.instrument_type)); db.add(instrument); db.flush()
    elif instrument.type.value != data.instrument_type: raise HTTPException(422, "Ticker is already registered with another type")
    mapping = db.query(InstrumentMapping).filter(InstrumentMapping.sector_equity_id == sector.pk_equity_id, InstrumentMapping.instrument_equity_id == instrument.pk_equity_id).first()
    if not mapping: mapping = InstrumentMapping(sector_equity_id=sector.pk_equity_id, instrument_equity_id=instrument.pk_equity_id); db.add(mapping); db.commit(); db.refresh(mapping)
    return {"mapping_id": mapping.pk_instrument_mapping_id, "sector_equity_id": sector.pk_equity_id, "instrument_equity_id": instrument.pk_equity_id, "ticker": instrument.ticker, "name": instrument.name, "instrument_type": instrument.type.value}


@router.post("/admin/refresh")
def refresh(_: object = Depends(get_current_admin), db: Session = Depends(get_db)):
    return {"data_quality": refresh_mapped_data(db)}


def compute_in_background(strategy_id: int) -> None:
    db = SessionLocal()
    try:
        compute(db, strategy_id)
    except Exception as exc:
        db.rollback()
        print(f"Anomaly Trading V2 compute failed: {exc}")
    finally:
        db.close()


@router.post("/admin/compute", status_code=status.HTTP_202_ACCEPTED)
def run_compute(tasks: BackgroundTasks, _: object = Depends(get_current_admin), db: Session = Depends(get_db)):
    tasks.add_task(compute_in_background, strategy(db).pk_strategy_id)
    return {"status": "queued", "message": "Computation started; published results stay available until it completes."}


@router.post("/admin/sectors/{sector_id}/track-instruments")
def track_instruments(sector_id: int, _: object = Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        return track_sector_instruments(db, strategy(db).pk_strategy_id, sector_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/admin/sectors")
def admin_sectors(_: object = Depends(get_current_admin), db: Session = Depends(get_db)):
    latest_run = db.scalar(select(StrategyRun.pk_strategy_run_id).join(Strategy).where(Strategy.key == "anomaly-trading").order_by(StrategyRun.computed_at.desc()).limit(1))
    if not latest_run: return []
    mapped_equity = aliased(Equity)
    rows = db.execute(
        select(
            StrategyPlan.sector_equity_id, Equity.name, func.count(func.distinct(StrategyPlan.pk_strategy_plan_id)),
            func.count(func.distinct(InstrumentMapping.pk_instrument_mapping_id)).filter(mapped_equity.type == EquityType.STOCK),
            func.count(func.distinct(InstrumentMapping.pk_instrument_mapping_id)).filter(mapped_equity.type == EquityType.ETF),
        )
        .join(Equity, Equity.pk_equity_id == StrategyPlan.sector_equity_id)
        .outerjoin(InstrumentMapping, InstrumentMapping.sector_equity_id == StrategyPlan.sector_equity_id)
        .outerjoin(mapped_equity, mapped_equity.pk_equity_id == InstrumentMapping.instrument_equity_id)
        .where(StrategyPlan.strategy_run_id == latest_run, InstrumentMapping.active.is_(True))
        .group_by(StrategyPlan.sector_equity_id, Equity.name)
        .order_by(Equity.name)
    ).all()
    return [{"sector_equity_id": sector_id, "sector": name, "qualified_windows": windows, "stock_mapping_count": stocks, "etf_mapping_count": etfs}
            for sector_id, name, windows, stocks, etfs in rows]


@router.get("/admin/sectors/{sector_id}/mappings")
def admin_sector_mappings(sector_id: int, _: object = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Equity.name, Equity.ticker, Equity.type).join(InstrumentMapping, InstrumentMapping.instrument_equity_id == Equity.pk_equity_id)
                      .where(InstrumentMapping.sector_equity_id == sector_id, InstrumentMapping.active.is_(True))
                      .order_by(Equity.type, Equity.ticker)).all()
    return [{"name": name, "ticker": ticker, "instrument_type": kind.value} for name, ticker, kind in rows]


@router.get("/admin/latest")
def latest(_: object = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.query(StrategyRun).join(Strategy).filter(Strategy.key == "anomaly-trading").order_by(StrategyRun.computed_at.desc()).first()
    if not item: return {"run": None, "plans": []}
    # One joined plan read and one grouped sector read: do not call
    # plan_response/db.get inside a result loop.
    plans = [serialized_plan(row) for row in db.execute(published_plan_query(item.pk_strategy_run_id)).all()]
    status_rows = db.execute(
        select(
            StrategyPlan.sector_equity_id, Equity.name, func.count(StrategyPlan.pk_strategy_plan_id),
            func.count(PlanInstrument.pk_plan_instrument_id),
        )
        .join(Equity, Equity.pk_equity_id == StrategyPlan.sector_equity_id)
        .outerjoin(PlanInstrument, (PlanInstrument.strategy_plan_id == StrategyPlan.pk_strategy_plan_id) & PlanInstrument.is_recommended.is_(True))
        .where(StrategyPlan.strategy_run_id == item.pk_strategy_run_id)
        .group_by(StrategyPlan.sector_equity_id, Equity.name)
    ).all()
    mapping_rows = db.execute(
        select(
            InstrumentMapping.sector_equity_id,
            func.count(InstrumentMapping.pk_instrument_mapping_id).filter(Equity.type == EquityType.STOCK),
            func.count(InstrumentMapping.pk_instrument_mapping_id).filter(Equity.type == EquityType.ETF),
        )
        .join(Equity, Equity.pk_equity_id == InstrumentMapping.instrument_equity_id)
        .where(InstrumentMapping.active.is_(True))
        .group_by(InstrumentMapping.sector_equity_id)
    ).all()
    mapping_counts = {sector_id: (stocks, etfs) for sector_id, stocks, etfs in mapping_rows}
    sectors = [{"sector_equity_id": sector_id, "sector": name, "qualified_windows": windows, "recommended_instruments": recommendations}
               | {"stock_mapping_count": mapping_counts.get(sector_id, (0, 0))[0], "etf_mapping_count": mapping_counts.get(sector_id, (0, 0))[1]}
               for sector_id, name, windows, recommendations in status_rows]
    return {"run": {"id": item.pk_strategy_run_id, "computed_at": item.computed_at, "data_quality": item.data_quality}, "plans": plans, "sectors": sectors}

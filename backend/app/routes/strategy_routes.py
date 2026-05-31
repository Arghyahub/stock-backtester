from app.schemas.strategy_schema import CreateStrategyResponse
from app.schemas.strategy_schema import GetStrategy
from app.schemas.strategy_schema import GetStrategies
from fastapi import status
from app.repositories.strategy_repository import StrategyRepository
from sqlalchemy.orm import Session
from fastapi import Response
from app.db.database import get_db
from fastapi import Depends
from app.schemas.strategy_schema import CreateStrategyRequest
from fastapi import APIRouter

strategy_router = APIRouter(
    prefix="/strategy",
    tags=["Strategy"]
)

@strategy_router.get("/", response_model=GetStrategies)
def get_strategies(db: Session = Depends(get_db)):
    strategies =  StrategyRepository.get_strategies(db)
    return {"strategies": strategies}


@strategy_router.post(
    "/",
    response_model=CreateStrategyResponse
)
def create_strategy(
    data: CreateStrategyRequest,
    db: Session = Depends(get_db),
    response: Response = Response
):
    strategy_id = StrategyRepository.create_strategy(db, data)
    response.status_code = status.HTTP_201_CREATED
    return {"strategy_id": strategy_id}
from app.db.models import Strategy
from app.schemas.strategy_schema import CreateStrategyRequest
from sqlalchemy.orm import Session
class StrategyRepository:
    @staticmethod
    def get_strategies(db: Session):
        return db.query(Strategy).order_by(Strategy.pk_strategy_id.asc()).all()

    @staticmethod
    def create_strategy(db: Session, data: CreateStrategyRequest):
        strategy = Strategy(
            name=data.name,
            description=data.description,
            key=data.key
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        return strategy.pk_strategy_id
        
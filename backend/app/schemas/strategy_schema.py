
from pydantic import Field
from pydantic import BaseModel

class GetStrategy(BaseModel):
    strategy_id: int = Field(validation_alias="pk_strategy_id")
    name: str

    model_config = {
        "from_attributes": True
    }

class GetStrategies(BaseModel):
    strategies: list[GetStrategy]

class CreateStrategyRequest(BaseModel):
    name: str
    description: str

class StrategyResponse(BaseModel):
    pk_strategy_id: int
    name: str
    description: str

    model_config = {
        "from_attributes": True
    }
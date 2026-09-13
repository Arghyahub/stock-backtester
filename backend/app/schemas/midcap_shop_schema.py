from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class RecordMidcapShopTradeRequest(BaseModel):
    action: Literal["buy", "average", "sell"]
    ticker: str = Field(min_length=1, max_length=32)
    execution_price: float = Field(gt=0)
    quantity: int | None = Field(default=None, gt=0)
    execution_date: date

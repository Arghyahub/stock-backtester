from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.database import Base
from app.db.enums import EquityType


class Equity(Base):
    __tablename__ = "equities"

    pk_equity_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    ticker: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    type: Mapped[EquityType] = mapped_column(
        Enum(EquityType),
        nullable=False
    )
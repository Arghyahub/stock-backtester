from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.database import Base


class RelationStockEquity(Base):
    __tablename__ = "relation_stock_equity"

    pk_relation_stock_equity_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    parent_equity_id: Mapped[int] = mapped_column(
        ForeignKey("equities.pk_equity_id"),
        nullable=False
    )

    stock_equity_id: Mapped[int] = mapped_column(
        ForeignKey("equities.pk_equity_id"),
        nullable=False
    )
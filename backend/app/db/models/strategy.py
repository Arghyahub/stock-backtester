from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column
from app.db.database import Base
class Strategy(Base):
    __tablename__ = "strategies"
    pk_strategy_id = mapped_column(Integer, primary_key=True, index=True)
    name = mapped_column(String, index=True)
    key = mapped_column(String, index=True, unique=True)
    description = mapped_column(String)
    
from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.database import Base
from app.db.enums import UserType


class User(Base):
    __tablename__ = "users"

    pk_user_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    user_name: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    password: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    user_type: Mapped[UserType] = mapped_column(
        Enum(UserType),
        nullable=False
    )
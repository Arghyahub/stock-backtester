from app.db.enums import UserType
from app.core.security import verify_password
from app.core.security import hash_password
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.schemas.user_schema import CreateUserRequest


class UserRepository:

    @staticmethod
    def create_user(
        db: Session,
        data: CreateUserRequest
    ) -> User:

        user = User(
            user_name=data.user_name,
            password=hash_password(data.password),
            user_type=UserType.GENERAL
        )

        db.add(user)

        db.commit()

        db.refresh(user)

        return user

    @staticmethod
    def get_users(
        db: Session
    ) -> list[User]:

        return db.query(User).all()

    @staticmethod
    def get_user_by_id(
        db: Session,
        user_id: int
    ) -> User | None:

        return (
            db.query(User)
            .filter(User.pk_user_id == user_id)
            .first()
        )
    
    @staticmethod
    def login(
        db: Session,
        user_name: str,
        password: str
    ) -> User | None:

        user = (
            db.query(User)
            .filter(User.user_name == user_name)
            .first()
        )

        if not user:
            return None

        is_valid = verify_password(
            password,
            user.password
        )

        if not is_valid:
            return None

        return user
    
    @staticmethod
    def get_user_by_username(
        db: Session,
        user_name: str
    ) -> User | None:

        return (
            db.query(User)
            .filter(User.user_name == user_name)
            .first()
        )
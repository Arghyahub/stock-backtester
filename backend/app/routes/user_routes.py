from fastapi import Response
from app.schemas.user_schema import VerifyTokenResponse
from app.core.dependecies import get_current_user
from app.db.models import User
from email.header import Header
from app.core.security import create_access_token
from app.schemas.user_schema import LoginRequest
from app.schemas.user_schema import LoginResponse
from app.repositories.user_repository import UserRepository
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from sqlalchemy.orm import Session

from app.db.database import get_db

from app.schemas.user_schema import (
    CreateUserRequest,
    UserResponse
)

user_router = APIRouter(
    prefix="/user",
    tags=["Users"]
)


@user_router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_user(
    data: CreateUserRequest,
    db: Session = Depends(get_db)
):

    existing_user = UserRepository.get_user_by_username(
        db=db,
        user_name=data.user_name
    )

    if existing_user:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )

    user = UserRepository.create_user(
        db=db,
        data=data
    )

    return user

@user_router.post(
    "/login",
    response_model=LoginResponse
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
    response: Response = Response
):

    user = UserRepository.login(
        db=db,
        user_name=data.user_name,
        password=data.password
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    access_token = create_access_token(
        user.pk_user_id
    )

    response.status_code = status.HTTP_200_OK
    return {
        "access_token": access_token
    }

# current_user: User = Depends(get_current_user)

@user_router.get(
    "/verify",
    response_model=VerifyTokenResponse
)
def verify_token(
    user: User = Depends(get_current_user),
    response: Response = Response
):
    response.status_code = status.HTTP_200_OK
    return {"success": True}

from pydantic import BaseModel

from app.db.enums import UserType


class CreateUserRequest(BaseModel):
    user_name: str
    password: str


class UserResponse(BaseModel):
    pk_user_id: int
    user_name: str
    user_type: UserType

    model_config = {
        "from_attributes": True
    }

class LoginRequest(BaseModel):
    user_name: str
    password: str


class LoginResponse(BaseModel):
    access_token: str

class VerifyTokenResponse(BaseModel):
    success: bool
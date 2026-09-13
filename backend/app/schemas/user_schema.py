from pydantic import BaseModel, Field, field_validator

from app.db.enums import UserType


class CreateUserRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Enter a valid email address")
        return normalized


class UserResponse(BaseModel):
    pk_user_id: int
    email: str
    user_type: UserType

    model_config = {
        "from_attributes": True
    }

class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginResponse(BaseModel):
    access_token: str

class VerifyTokenResponse(BaseModel):
    success: bool


class CurrentUserResponse(BaseModel):
    pk_user_id: int
    email: str
    user_type: UserType

    model_config = {"from_attributes": True}

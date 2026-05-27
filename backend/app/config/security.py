from jose import JWTError
from app.config.config import env
from datetime import timedelta
from datetime import timezone
from datetime import datetime
from pwdlib import PasswordHash
from jose import jwt

password_hash = PasswordHash.recommended()


def hash_password(
    password: str
) -> str:

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return password_hash.verify(
        plain_password,
        hashed_password
    )

def create_access_token(
    user_id: int
) -> str:

    expire = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=env.JWT_EXPIRE_MINUTES
    )

    payload = {
        "user_id": user_id,
        "exp": expire
    }

    return jwt.encode(
        payload,
        env.JWT_SECRET,
        algorithm=env.JWT_ALGORITHM
    )


def decode_access_token(
    token: str
):

    try:

        payload = jwt.decode(
            token,
            env.JWT_SECRET,
            algorithms=[env.JWT_ALGORITHM]
        )

        return payload

    except JWTError:

        return None
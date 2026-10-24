from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(subject: str, extra: dict[str, Any], minutes: int | None = None, days: int | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if days is not None:
        exp = now + timedelta(days=days)
    else:
        exp = now + timedelta(minutes=minutes or settings.access_token_expire_minutes)
    payload = {"sub": subject, "iat": now, "exp": exp, **extra}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload

from app.core.security import decode_token
from app.db.session import get_db
from app.models.entities import User

oauth2 = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    user = db.query(User).options(joinedload(User.role), joinedload(User.region), joinedload(User.institution)).filter(User.id == int(user_id)).first()
    if not user or not user.is_active or getattr(user, "account_status", "active") != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or missing")
    token_version = int(payload.get("tv", 0))
    if token_version != int(getattr(user, "token_version", 0) or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return user


def require_roles(*codes: str):
    def _inner(user: User = Depends(get_current_user)) -> User:
        if user.role.code not in codes and user.role.code != "super_admin":
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _inner

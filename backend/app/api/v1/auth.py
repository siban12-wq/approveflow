from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.security import create_token, verify_password
from app.db.session import get_db
from app.models.entities import User

router = APIRouter()


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.code,
        "role_name": user.role.name,
        "region_id": user.region_id,
        "region_name": user.region.name if user.region else None,
        "institution_id": user.institution_id,
        "institution_name": user.institution.name if user.institution else None,
        "demo": True,
    }


@router.post("/login", response_model=TokenOut)
def login(body: LoginBody, db: Session = Depends(get_db)) -> TokenOut:
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.region), joinedload(User.institution))
        .filter(User.email == body.email.lower())
        .first()
    )
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    settings = get_settings()
    access = create_token(str(user.id), {"role": user.role.code})
    refresh = create_token(str(user.id), {"role": user.role.code, "typ": "refresh"}, days=settings.refresh_token_expire_days)
    return TokenOut(access_token=access, refresh_token=refresh, user=_user_payload(user))


class RefreshBody(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshBody, db: Session = Depends(get_db)) -> TokenOut:
    from app.core.security import decode_token

    try:
        payload = decode_token(body.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("typ") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.region), joinedload(User.institution))
        .filter(User.id == int(payload["sub"]))
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    settings = get_settings()
    return TokenOut(
        access_token=create_token(str(user.id), {"role": user.role.code}),
        refresh_token=create_token(str(user.id), {"role": user.role.code, "typ": "refresh"}, days=settings.refresh_token_expire_days),
        user=_user_payload(user),
    )


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return _user_payload(user)


@router.get("/demo-users")
def demo_users(db: Session = Depends(get_db)) -> list[dict]:
    users = db.query(User).options(joinedload(User.role)).filter(User.email.like("%@approveflow.demo")).all()
    return [{"email": u.email, "full_name": u.full_name, "role": u.role.code, "role_name": u.role.name} for u in users]

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import (
    GENERIC_AUTH_ERROR,
    create_token,
    decode_token,
    hash_password,
    hash_token,
    new_url_token,
    validate_password,
    verify_password,
)
from app.db.session import get_db
from app.models.entities import AuthToken, Institution, LoginAttempt, Region, Role, User
from app.services.audit import write_audit
from app.services.email import get_email_provider

router = APIRouter()

PUBLIC_SIGNUP_ROLES = {"institution_user"}
PRIVILEGED_ROLES = {
    "super_admin",
    "bureau_officer",
    "regional_officer",
    "scrutiny_officer",
    "committee_member",
    "evc_coordinator",
    "competent_authority",
}


def _clean_email(v: str) -> str:
    s = (v or "").strip().lower()
    if "@" not in s or "." not in s.split("@")[-1]:
        raise ValueError("Invalid email address format.")
    return s


class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _clean_email(v)


class RegisterBody(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    mobile: str | None = Field(default=None, max_length=20)
    institution_name: str = Field(min_length=3, max_length=255)
    institution_code: str | None = Field(default=None, max_length=32)
    region_id: int | None = None
    requested_role: str = "institution_user"
    password: str
    confirm_password: str
    accept_terms: bool

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _clean_email(v)


class ForgotBody(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _clean_email(v)


class ResetBody(BaseModel):
    token: str
    password: str
    confirm_password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


def _user_payload(user: User) -> dict:
    status = getattr(user, "account_status", "active") or "active"
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
        "account_status": status,
        "email_verified": bool(getattr(user, "email_verified", False)),
        "mobile": getattr(user, "mobile", None),
        "demo": user.email.endswith("@approveflow.demo"),
    }


def _issue_tokens(user: User) -> TokenOut:
    settings = get_settings()
    extra = {"role": user.role.code, "tv": int(getattr(user, "token_version", 0) or 0)}
    access = create_token(str(user.id), extra)
    refresh = create_token(str(user.id), {**extra, "typ": "refresh"}, days=settings.refresh_token_expire_days)
    return TokenOut(access_token=access, refresh_token=refresh, user=_user_payload(user))


def _load_user_by_email(db: Session, email: str) -> User | None:
    return (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.region), joinedload(User.institution))
        .filter(User.email == email.lower())
        .first()
    )


def _locked(db: Session, email: str) -> bool:
    settings = get_settings()
    since = clock.now() - timedelta(minutes=settings.login_lock_minutes)
    failures = (
        db.query(LoginAttempt)
        .filter(LoginAttempt.email == email.lower(), LoginAttempt.success.is_(False), LoginAttempt.created_at >= since)
        .count()
    )
    return failures >= settings.login_lock_threshold


def _record_attempt(db: Session, email: str, ip: str | None, success: bool) -> None:
    db.add(LoginAttempt(email=email.lower(), ip=ip, success=success, created_at=clock.now()))


@router.post("/login", response_model=TokenOut)
@limiter.limit("12/minute")
def login(request: Request, body: LoginBody, db: Session = Depends(get_db)) -> TokenOut:
    email = body.email.lower()
    ip = request.client.host if request.client else None
    if _locked(db, email):
        write_audit(
            db,
            actor_id=None,
            actor_role="anonymous",
            actor_label=email,
            action="login_locked",
            entity_type="user",
            entity_id=email,
            ip=ip,
        )
        db.commit()
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again later.")
    user = _load_user_by_email(db, email)
    valid = bool(user and verify_password(body.password, user.hashed_password))
    status = getattr(user, "account_status", "active") if user else None
    if not valid or not user or not user.is_active or status != "active":
        _record_attempt(db, email, ip, False)
        write_audit(
            db,
            actor_id=user.id if user else None,
            actor_role=user.role.code if user else "anonymous",
            actor_label=email,
            action="login_failed",
            entity_type="user",
            entity_id=str(user.id) if user else email,
            ip=ip,
        )
        db.commit()
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
    _record_attempt(db, email, ip, True)
    user.last_login_at = clock.now()
    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.email,
        action="login",
        entity_type="user",
        entity_id=user.id,
        ip=ip,
    )
    db.commit()
    db.refresh(user)
    return _issue_tokens(user)


class RefreshBody(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshBody, db: Session = Depends(get_db)) -> TokenOut:
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
    if not user or not user.is_active or getattr(user, "account_status", "active") != "active":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if int(payload.get("tv", 0)) != int(getattr(user, "token_version", 0) or 0):
        raise HTTPException(status_code=401, detail="Session expired")
    return _issue_tokens(user)


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    user.token_version = int(getattr(user, "token_version", 0) or 0) + 1
    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.email,
        action="logout",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return _user_payload(user)


@router.get("/catalog")
def catalog(db: Session = Depends(get_db)) -> dict:
    regions = db.query(Region).order_by(Region.name).all()
    institutions = (
        db.query(Institution).order_by(Institution.name).limit(80).all()
    )
    return {
        "regions": [{"id": r.id, "code": r.code, "name": r.name} for r in regions],
        "institutions": [
            {"id": i.id, "code": i.code, "name": i.name, "region_id": i.region_id} for i in institutions
        ],
        "requestable_roles": [
            {"code": "institution_user", "name": "Institution Administrator"},
        ],
        "note": "Privileged officer accounts are provisioned by a system administrator. Institution registration requires verification.",
    }


@router.post("/register")
@limiter.limit("6/minute")
def register(request: Request, body: RegisterBody, db: Session = Depends(get_db)) -> dict:
    if not body.accept_terms:
        raise HTTPException(status_code=400, detail="You must accept the terms of use.")
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    policy = validate_password(body.password)
    if policy:
        raise HTTPException(status_code=400, detail=policy)
    role_code = (body.requested_role or "institution_user").strip()
    if role_code in PRIVILEGED_ROLES or role_code not in PUBLIC_SIGNUP_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Public registration is limited to institution administrator accounts. Privileged roles are provisioned by an authorised administrator.",
        )
    email = body.email.lower()
    if _load_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    role = db.query(Role).filter(Role.code == "institution_user").one()
    institution = None
    if body.institution_code:
        institution = db.query(Institution).filter(Institution.code == body.institution_code.strip().upper()).first()
    user = User(
        email=email,
        full_name=body.full_name.strip(),
        hashed_password=hash_password(body.password),
        role_id=role.id,
        region_id=body.region_id or (institution.region_id if institution else None),
        institution_id=institution.id if institution else None,
        is_active=False,
        mobile=(body.mobile or "").strip() or None,
        account_status="pending",
        email_verified=False,
        requested_role="institution_user",
        requested_institution_name=body.institution_name.strip(),
        token_version=0,
        created_at=clock.now(),
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        actor_id=user.id,
        actor_role="institution_user",
        actor_label=user.email,
        action="register_requested",
        entity_type="user",
        entity_id=user.id,
        new_value=body.institution_name,
        ip=request.client.host if request.client else None,
    )
    settings = get_settings()
    raw = new_url_token()
    db.add(
        AuthToken(
            user_id=user.id,
            purpose="verify",
            token_hash=hash_token(raw),
            expires_at=clock.now() + timedelta(hours=24),
            created_at=clock.now(),
        )
    )
    verify_link = f"{settings.frontend_url.rstrip('/')}/#/verify-email?token={raw}"
    provider = get_email_provider()
    delivery = provider.send(
        user.email,
        "Verify your ApproveFlow account",
        f"Welcome to ApproveFlow.\n\nYour institution account is pending verification.\nConfirm this email: {verify_link}\n\nAn authorised administrator must approve access before you can sign in.\nThis is a simulated demo environment.",
        db,
    )
    db.commit()
    return {
        "ok": True,
        "status": "pending",
        "message": "Registration received. Verify your email if a message is available, then wait for administrator approval before signing in. An institution name is not treated as proof of institutional identity.",
        "email_delivery": "console_sink" if delivery == "queued_console" else delivery,
    }


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, body: ForgotBody, db: Session = Depends(get_db)) -> dict:
    generic = {
        "ok": True,
        "message": "If an account exists for that email, a reset link has been issued. Check the development email sink when SMTP is not configured.",
    }
    user = _load_user_by_email(db, body.email)
    if user and user.is_active and getattr(user, "account_status", "active") == "active":
        settings = get_settings()
        raw = new_url_token()
        db.add(
            AuthToken(
                user_id=user.id,
                purpose="reset",
                token_hash=hash_token(raw),
                expires_at=clock.now() + timedelta(minutes=settings.password_reset_expire_minutes),
                created_at=clock.now(),
            )
        )
        link = f"{settings.frontend_url.rstrip('/')}/#/reset-password?token={raw}"
        get_email_provider().send(
            user.email,
            "Reset your ApproveFlow password",
            f"Use this single-use link within {settings.password_reset_expire_minutes} minutes:\n{link}\n\nIf you did not request this, ignore the message.",
            db,
        )
        write_audit(
            db,
            actor_id=user.id,
            actor_role=user.role.code,
            actor_label=user.email,
            action="password_reset_requested",
            entity_type="user",
            entity_id=user.id,
            ip=request.client.host if request.client else None,
        )
        db.commit()
    else:
        db.commit()
    return generic


@router.post("/reset-password")
def reset_password(body: ResetBody, db: Session = Depends(get_db)) -> dict:
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    policy = validate_password(body.password)
    if policy:
        raise HTTPException(status_code=400, detail=policy)
    token = (
        db.query(AuthToken)
        .filter(AuthToken.token_hash == hash_token(body.token), AuthToken.purpose == "reset")
        .first()
    )
    if not token or token.used_at is not None or clock.aware(token.expires_at) < clock.now():
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    user = db.get(User, token.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    user.hashed_password = hash_password(body.password)
    user.token_version = int(getattr(user, "token_version", 0) or 0) + 1
    token.used_at = clock.now()
    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.email,
        action="password_reset_completed",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    return {"ok": True, "message": "Password updated. Sign in with your new password."}


@router.post("/verify-email")
def verify_email(body: dict, db: Session = Depends(get_db)) -> dict:
    raw = str(body.get("token") or "")
    token = (
        db.query(AuthToken)
        .filter(AuthToken.token_hash == hash_token(raw), AuthToken.purpose == "verify")
        .first()
    )
    if not token or token.used_at is not None or clock.aware(token.expires_at) < clock.now():
        raise HTTPException(status_code=400, detail="This verification link is invalid or has expired.")
    user = db.get(User, token.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="This verification link is invalid or has expired.")
    user.email_verified = True
    token.used_at = clock.now()
    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.email,
        action="email_verified",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    return {"ok": True, "message": "Email verified. An administrator must still approve your account before sign-in."}


@router.get("/demo-users")
def demo_users(db: Session = Depends(get_db)) -> list[dict]:
    users = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.email.like("%@approveflow.demo"))
        .all()
    )
    return [{"email": u.email, "full_name": u.full_name, "role": u.role.code, "role_name": u.role.name} for u in users]


@router.get("/dev/outbox")
def dev_outbox(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Not found")
    from app.models.entities import EmailOutbox

    rows = db.query(EmailOutbox).order_by(EmailOutbox.id.desc()).limit(20).all()
    return {
        "provider": "console" if not settings.smtp_enabled else "smtp",
        "notice": "Development email sink. Messages are not claimed as delivered unless SMTP is configured and succeeds.",
        "messages": [
            {"id": r.id, "to": r.to_address, "subject": r.subject, "body": r.body, "provider": r.provider, "created_at": r.created_at.isoformat()}
            for r in rows
        ],
    }

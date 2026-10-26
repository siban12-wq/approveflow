from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.core.config import get_settings
from app.core.deps import require_roles
from app.db.session import SessionLocal, engine as db_engine, get_db
from app.jobs.scheduler import run_job
from app.jobs.tasks import JOBS
from app.core.security import hash_password, new_url_token, validate_password
from app.models.entities import (
    AlertRule,
    Base,
    EscalationRule,
    Institution,
    JobRun,
    NotificationTemplate,
    Region,
    Role,
    User,
    WorkflowStage,
    WorkflowTemplate,
)
from app.services.audit import write_audit
from app.services.email import get_email_provider

router = APIRouter()


@router.get("/workflow-templates")
def list_templates(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "bureau_officer"))) -> list[dict]:
    tpls = db.query(WorkflowTemplate).options(joinedload(WorkflowTemplate.stages)).all()
    return [
        {
            "id": t.id,
            "code": t.code,
            "name": t.name,
            "description": t.description,
            "is_active": t.is_active,
            "version": t.version,
            "stages": [
                {
                    "id": s.id,
                    "order_no": s.order_no,
                    "stage_code": s.stage_code,
                    "name": s.name,
                    "sla_days": s.sla_days,
                    "allowed_roles": s.allowed_roles,
                    "requires_remarks": s.requires_remarks,
                }
                for s in sorted(t.stages, key=lambda x: x.order_no)
            ],
        }
        for t in tpls
    ]


class StagePatch(BaseModel):
    sla_days: int | None = None
    allowed_roles: list[str] | None = None
    requires_remarks: bool | None = None
    name: str | None = None


class TemplatePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    stages: list[dict] | None = None


@router.put("/workflow-templates/{template_id}")
def update_template(
    template_id: int,
    body: TemplatePatch,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin")),
) -> dict:
    tpl = db.get(WorkflowTemplate, template_id)
    if not tpl:
        raise HTTPException(404, "Template not found")
    if body.name is not None:
        tpl.name = body.name
    if body.description is not None:
        tpl.description = body.description
    if body.is_active is not None:
        tpl.is_active = body.is_active
    if body.stages:
        for item in body.stages:
            st = db.get(WorkflowStage, item.get("id"))
            if st and st.template_id == tpl.id:
                if "sla_days" in item:
                    st.sla_days = int(item["sla_days"])
                if "allowed_roles" in item:
                    st.allowed_roles = item["allowed_roles"]
                if "requires_remarks" in item:
                    st.requires_remarks = bool(item["requires_remarks"])
    tpl.version += 1
    db.commit()
    return {"ok": True, "version": tpl.version}


@router.get("/alert-rules")
def alert_rules(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "bureau_officer"))) -> list[dict]:
    return [
        {
            "id": r.id,
            "code": r.code,
            "entity_type": r.entity_type,
            "trigger_type": r.trigger_type,
            "offset_days": r.offset_days,
            "channels": r.channels,
            "recipient_roles": r.recipient_roles,
            "severity": r.severity,
            "is_active": r.is_active,
            "template_id": r.template_id,
        }
        for r in db.query(AlertRule).all()
    ]


class AlertPatch(BaseModel):
    offset_days: int | None = None
    is_active: bool | None = None
    severity: str | None = None
    channels: dict | None = None
    recipient_roles: list[str] | None = None


@router.put("/alert-rules/{rule_id}")
def put_alert(rule_id: int, body: AlertPatch, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> dict:
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(rule, k, v)
    db.commit()
    return {"ok": True}


@router.get("/escalation-rules")
def esc_rules(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "bureau_officer"))) -> list[dict]:
    return [
        {
            "id": r.id,
            "entity_type": r.entity_type,
            "level": r.level,
            "threshold_days_overdue": r.threshold_days_overdue,
            "escalate_to_role": r.escalate_to_role,
            "region_scoped": r.region_scoped,
        }
        for r in db.query(EscalationRule).all()
    ]


class EscPatch(BaseModel):
    threshold_days_overdue: int | None = None
    escalate_to_role: str | None = None


@router.put("/escalation-rules/{rule_id}")
def put_esc(rule_id: int, body: EscPatch, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> dict:
    rule = db.get(EscalationRule, rule_id)
    if not rule:
        raise HTTPException(404, "Not found")
    if body.threshold_days_overdue is not None:
        rule.threshold_days_overdue = body.threshold_days_overdue
    if body.escalate_to_role is not None:
        rule.escalate_to_role = body.escalate_to_role
    db.commit()
    return {"ok": True}


@router.get("/notification-templates")
def templates(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> list[dict]:
    return [{"id": t.id, "code": t.code, "subject": t.subject, "body": t.body} for t in db.query(NotificationTemplate).all()]


class TplPatch(BaseModel):
    subject: str | None = None
    body: str | None = None


@router.put("/notification-templates/{tid}")
def put_tpl(tid: int, body: TplPatch, db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> dict:
    t = db.get(NotificationTemplate, tid)
    if not t:
        raise HTTPException(404, "Not found")
    if body.subject is not None:
        t.subject = body.subject
    if body.body is not None:
        t.body = body.body
    db.commit()
    return {"ok": True}


@router.post("/jobs/{name}/run")
def run_now(name: str, user: User = Depends(require_roles("super_admin", "bureau_officer"))) -> dict:
    if name not in JOBS:
        raise HTTPException(404, f"Unknown job {name}")
    result = run_job(name)
    return {"ok": True, "name": name, "alerts_created": result.alerts_created, "items_checked": result.items_checked}


@router.get("/jobs/runs")
def job_runs(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "bureau_officer"))) -> list[dict]:
    rows = db.query(JobRun).order_by(JobRun.id.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "items_checked": r.items_checked,
            "alerts_created": r.alerts_created,
            "errors": r.errors,
        }
        for r in rows
    ]


@router.post("/demo/advance-clock")
def advance_clock(days: int = 7, user: User = Depends(require_roles("super_admin"))) -> dict:
    if not get_settings().demo_mode:
        raise HTTPException(403, "Demo clock is disabled outside demo mode")
    now = clock.advance_days(days)
    return {"ok": True, "now": now.isoformat(), "offset_days": int(clock._offset.days)}


def _account_row(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role.code,
        "role_name": u.role.name,
        "region_id": u.region_id,
        "region_name": u.region.name if u.region else None,
        "institution_id": u.institution_id,
        "institution_name": u.institution.name if u.institution else None,
        "open_case_count": u.open_case_count,
        "is_active": u.is_active,
        "account_status": u.account_status or "active",
        "email_verified": bool(getattr(u, "email_verified", False)),
        "requested_role": getattr(u, "requested_role", None),
        "requested_institution_name": getattr(u, "requested_institution_name", None),
        "mobile": getattr(u, "mobile", None),
        "last_login_at": u.last_login_at.isoformat() if getattr(u, "last_login_at", None) else None,
        "created_at": u.created_at.isoformat() if getattr(u, "created_at", None) else None,
        "status_reason": getattr(u, "status_reason", None),
    }


@router.get("/users")
def list_users(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin", "bureau_officer", "regional_officer")),
) -> list[dict]:
    q = db.query(User).options(joinedload(User.role), joinedload(User.region), joinedload(User.institution))
    if user.role.code == "regional_officer" and user.region_id:
        q = q.filter(User.region_id == user.region_id)
    if status:
        q = q.filter(User.account_status == status)
    return [_account_row(u) for u in q.order_by(User.id.desc()).all()]


class AccountAction(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    institution_id: int | None = None
    region_id: int | None = None
    role: str | None = None


def _clean_email(v: str) -> str:
    s = (v or "").strip().lower()
    if "@" not in s or "." not in s.split("@")[-1]:
        raise ValueError("Invalid email address format.")
    return s


class ProvisionBody(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=2, max_length=255)
    role: str
    reason: str = Field(min_length=3, max_length=500)
    region_id: int | None = None
    institution_id: int | None = None
    mobile: str | None = None
    password: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _clean_email(v)


def _get_role(db: Session, code: str) -> Role:
    role = db.query(Role).filter(Role.code == code).first()
    if not role:
        raise HTTPException(400, f"Unknown role {code}")
    return role


@router.post("/accounts/{user_id}/approve")
def approve_account(
    user_id: int,
    body: AccountAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("super_admin")),
) -> dict:
    target = db.query(User).options(joinedload(User.role)).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "Account not found")
    if target.role.code in {"super_admin"} and actor.id != target.id:
        pass
    if body.institution_id:
        inst = db.get(Institution, body.institution_id)
        if not inst:
            raise HTTPException(400, "Institution not found")
        target.institution_id = inst.id
        target.region_id = inst.region_id
    elif body.region_id:
        if not db.get(Region, body.region_id):
            raise HTTPException(400, "Region not found")
        target.region_id = body.region_id
    if body.role:
        if body.role == "super_admin" and actor.role.code != "super_admin":
            raise HTTPException(403, "Cannot assign system administrator")
        target.role_id = _get_role(db, body.role).id
    target.account_status = "active"
    target.is_active = True
    target.approved_at = clock.now()
    target.approved_by_id = actor.id
    target.status_reason = body.reason
    write_audit(
        db,
        actor_id=actor.id,
        actor_role=actor.role.code,
        actor_label=actor.email,
        action="account_approved",
        entity_type="user",
        entity_id=target.id,
        reason=body.reason,
        new_value=target.email,
    )
    db.commit()
    return {"ok": True}


@router.post("/accounts/{user_id}/reject")
def reject_account(
    user_id: int,
    body: AccountAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("super_admin")),
) -> dict:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Account not found")
    target.account_status = "rejected"
    target.is_active = False
    target.status_reason = body.reason
    write_audit(
        db,
        actor_id=actor.id,
        actor_role=actor.role.code,
        actor_label=actor.email,
        action="account_rejected",
        entity_type="user",
        entity_id=target.id,
        reason=body.reason,
    )
    db.commit()
    return {"ok": True}


@router.post("/accounts/{user_id}/suspend")
def suspend_account(
    user_id: int,
    body: AccountAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("super_admin")),
) -> dict:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Account not found")
    if target.id == actor.id:
        raise HTTPException(400, "You cannot suspend your own account")
    target.account_status = "suspended"
    target.is_active = False
    target.token_version = int(target.token_version or 0) + 1
    target.status_reason = body.reason
    write_audit(
        db,
        actor_id=actor.id,
        actor_role=actor.role.code,
        actor_label=actor.email,
        action="account_suspended",
        entity_type="user",
        entity_id=target.id,
        reason=body.reason,
    )
    db.commit()
    return {"ok": True}


@router.post("/accounts/{user_id}/reactivate")
def reactivate_account(
    user_id: int,
    body: AccountAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("super_admin")),
) -> dict:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Account not found")
    target.account_status = "active"
    target.is_active = True
    target.status_reason = body.reason
    write_audit(
        db,
        actor_id=actor.id,
        actor_role=actor.role.code,
        actor_label=actor.email,
        action="account_reactivated",
        entity_type="user",
        entity_id=target.id,
        reason=body.reason,
    )
    db.commit()
    return {"ok": True}


@router.post("/accounts/{user_id}/role")
def assign_role(
    user_id: int,
    body: AccountAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("super_admin")),
) -> dict:
    if not body.role:
        raise HTTPException(400, "Role is required")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Account not found")
    old = db.get(Role, target.role_id)
    target.role_id = _get_role(db, body.role).id
    target.status_reason = body.reason
    write_audit(
        db,
        actor_id=actor.id,
        actor_role=actor.role.code,
        actor_label=actor.email,
        action="role_assigned",
        entity_type="user",
        entity_id=target.id,
        reason=body.reason,
        old_value=old.code if old else None,
        new_value=body.role,
    )
    db.commit()
    return {"ok": True}


@router.post("/accounts/provision")
def provision_account(
    body: ProvisionBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("super_admin")),
) -> dict:
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists.")
    if body.password:
        err = validate_password(body.password)
        if err:
            raise HTTPException(400, err)
        password = body.password
        generated = False
    else:
        password = f"Tmp#{new_url_token()[:10]}A1"
        generated = True
    role = _get_role(db, body.role)
    if body.institution_id and not db.get(Institution, body.institution_id):
        raise HTTPException(400, "Institution not found")
    if body.region_id and not db.get(Region, body.region_id):
        raise HTTPException(400, "Region not found")
    user = User(
        email=email,
        full_name=body.full_name.strip(),
        hashed_password=hash_password(password),
        role_id=role.id,
        region_id=body.region_id,
        institution_id=body.institution_id,
        is_active=True,
        mobile=body.mobile,
        account_status="active",
        email_verified=True,
        token_version=0,
        created_at=clock.now(),
        approved_at=clock.now(),
        approved_by_id=actor.id,
        status_reason=body.reason,
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        actor_id=actor.id,
        actor_role=actor.role.code,
        actor_label=actor.email,
        action="account_provisioned",
        entity_type="user",
        entity_id=user.id,
        reason=body.reason,
        new_value=f"{email}:{body.role}",
    )
    get_email_provider().send(
        email,
        "Your ApproveFlow account has been provisioned",
        f"An authorised administrator created your {role.name} account.\nSign-in email: {email}\n"
        + ("A temporary password was generated. Use forgot-password if you were not given credentials separately.\n" if generated else "Use the password provided by your administrator.\n")
        + "This is a simulated demo environment.",
        db,
    )
    db.commit()
    return {"ok": True, "id": user.id, "temporary_password_issued": generated}


@router.get("/jobs")
def list_jobs(user: User = Depends(require_roles("super_admin", "bureau_officer"))) -> list[str]:
    return list(JOBS.keys())


@router.post("/demo/reset")
def reset_demo(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin"))) -> dict:
    if not get_settings().demo_mode:
        raise HTTPException(403, "Reset is only available in demo mode")
    from app.seed import seed_all

    db.close()
    Base.metadata.drop_all(bind=db_engine)
    Base.metadata.create_all(bind=db_engine)
    fresh = SessionLocal()
    try:
        seed_all(fresh)
    finally:
        fresh.close()
    return {"ok": True, "notice": "Simulated demo data restored."}

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.core.config import get_settings
from app.core.deps import require_roles
from app.db.session import SessionLocal, engine as db_engine, get_db
from app.jobs.scheduler import run_job
from app.jobs.tasks import JOBS
from app.models.entities import (
    AlertRule,
    Base,
    EscalationRule,
    JobRun,
    NotificationTemplate,
    User,
    WorkflowStage,
    WorkflowTemplate,
)

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


@router.get("/users")
def list_users(db: Session = Depends(get_db), user: User = Depends(require_roles("super_admin", "bureau_officer", "regional_officer"))) -> list[dict]:
    rows = db.query(User).options(joinedload(User.role)).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.code,
            "region_id": u.region_id,
            "institution_id": u.institution_id,
            "open_case_count": u.open_case_count,
        }
        for u in rows
    ]


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

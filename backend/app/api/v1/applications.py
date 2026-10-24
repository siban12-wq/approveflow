from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Application, ApplicationStageHistory, Deficiency, Institution, User, WorkflowTemplate
from app.workflows.engine import TYPE_TO_TEMPLATE, engine

router = APIRouter()


def _scope(q, user: User):
    if user.role.code == "institution_user":
        return q.filter(Application.institution_id == user.institution_id)
    if user.role.code == "regional_officer" and user.region_id:
        return q.filter(Application.region_id == user.region_id)
    if user.role.code == "committee_member":
        return q.filter(Application.assigned_officer_id == user.id)
    return q


def _serialize(app: Application, db: Session, user: User) -> dict:
    inst = app.institution
    stage = app.current_stage
    officer = app.assigned_officer
    stages = sorted(app.template.stages, key=lambda s: s.order_no) if app.template else []
    return {
        "id": app.id,
        "app_id": app.app_id,
        "institution_id": app.institution_id,
        "institution": inst.name if inst else "",
        "region_id": app.region_id,
        "region": app.region.name if app.region else "",
        "application_type": app.application_type,
        "template_code": app.template.code if app.template else "",
        "current_stage": stage.stage_code if stage else None,
        "current_stage_name": stage.name if stage else None,
        "status": app.status,
        "decision": app.decision,
        "sla_status": app.sla_status,
        "sla_due_at": app.sla_due_at.isoformat() if app.sla_due_at else None,
        "stage_entered_at": app.stage_entered_at.isoformat() if app.stage_entered_at else None,
        "assigned_officer": officer.full_name if officer else None,
        "assigned_officer_id": app.assigned_officer_id,
        "age_days": clock.days_since(app.submitted_at),
        "last_updated_at": app.last_updated_at.isoformat() if app.last_updated_at else None,
        "simulated": True,
        "stages": [
            {"id": s.id, "code": s.stage_code, "name": s.name, "order_no": s.order_no, "sla_days": s.sla_days}
            for s in stages
        ],
        "allowed_actions": engine.allowed_actions(db, app, user),
        "human_oversight": "Automated alerts and recommendations support, but do not replace, decisions of the competent authority.",
    }


@router.get("")
def list_applications(
    q: str | None = None,
    stage: str | None = None,
    region_id: int | None = None,
    sla_status: str | None = None,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    query = db.query(Application).options(
        joinedload(Application.institution),
        joinedload(Application.region),
        joinedload(Application.current_stage),
        joinedload(Application.assigned_officer),
        joinedload(Application.template).joinedload(WorkflowTemplate.stages),
    )
    query = _scope(query, user)
    if q:
        like = f"%{q}%"
        query = query.join(Institution).filter(or_(Application.app_id.ilike(like), Institution.name.ilike(like)))
    if stage:
        query = query.join(Application.current_stage).filter(Application.current_stage.has(stage_code=stage))
    if region_id:
        query = query.filter(Application.region_id == region_id)
    if sla_status:
        query = query.filter(Application.sla_status == sla_status)
    total = query.count()
    rows = query.order_by(Application.last_updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "items": [_serialize(a, db, user) for a in rows]}


@router.get("/{application_id}")
def get_application(application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    app = (
        db.query(Application)
        .options(
            joinedload(Application.institution),
            joinedload(Application.region),
            joinedload(Application.current_stage),
            joinedload(Application.assigned_officer),
            joinedload(Application.template).joinedload(WorkflowTemplate.stages),
        )
        .filter(Application.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(404, "Application not found")
    if user.role.code == "institution_user" and app.institution_id != user.institution_id:
        raise HTTPException(403, "Institutions may only view their own records")
    data = _serialize(app, db, user)
    history = (
        db.query(ApplicationStageHistory)
        .filter(ApplicationStageHistory.application_id == app.id)
        .order_by(ApplicationStageHistory.created_at.asc())
        .all()
    )
    defs = db.query(Deficiency).filter(Deficiency.application_id == app.id).all()
    data["history"] = [
        {
            "from_stage": h.from_stage,
            "to_stage": h.to_stage,
            "action": h.action,
            "actor_role": h.actor_role,
            "reason": h.reason,
            "created_at": h.created_at.isoformat(),
            "duration_in_stage_hours": h.duration_in_stage_hours,
        }
        for h in history
    ]
    data["deficiencies"] = [
        {"id": d.id, "description": d.description, "status": d.status, "response_text": d.response_text}
        for d in defs
    ]
    data["case_summary"] = {
        "label": "Draft for official review",
        "text": (
            f"{app.app_id} — {app.institution.name} ({app.application_type}). "
            f"Current stage: {app.current_stage.name if app.current_stage else 'n/a'}. "
            f"SLA: {app.sla_status}. Decision: {app.decision or 'not recorded'}. "
            "This summary is generated for official review and is not a decision."
        ),
    }
    return data


class ForwardBody(BaseModel):
    remarks: str | None = None


class ReturnBody(BaseModel):
    reason: str = Field(min_length=15)
    target_stage_id: int | None = None


class RespondBody(BaseModel):
    response: str = Field(min_length=8)
    docs: list[str] = []


class AssignBody(BaseModel):
    officer_id: int
    reason: str = Field(min_length=8)


class DecisionBody(BaseModel):
    decision: str
    order_ref: str = Field(min_length=4)


class ClarifyBody(BaseModel):
    question: str = Field(min_length=10)


@router.post("/{application_id}/forward")
def forward(application_id: int, body: ForwardBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    app = engine.forward(db, application_id, user, body.remarks)
    db.commit()
    db.refresh(app)
    return {"ok": True, "stage": app.current_stage.stage_code if app.current_stage else None}


@router.post("/{application_id}/return")
def return_back(application_id: int, body: ReturnBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    app = engine.return_back(db, application_id, user, body.reason, body.target_stage_id)
    db.commit()
    return {"ok": True, "status": app.status}


@router.post("/{application_id}/respond")
def respond(application_id: int, body: RespondBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    app = engine.institution_respond(db, application_id, user, body.response, body.docs)
    db.commit()
    return {"ok": True, "stage": app.current_stage.stage_code if app.current_stage else None}


@router.post("/{application_id}/assign")
def assign(application_id: int, body: AssignBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    app = engine.reassign(db, application_id, user, body.officer_id, body.reason)
    db.commit()
    return {"ok": True, "assigned_officer_id": app.assigned_officer_id}


@router.post("/{application_id}/decision")
def decision(application_id: int, body: DecisionBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    app = engine.record_decision(db, application_id, user, body.decision, body.order_ref)
    db.commit()
    return {"ok": True, "decision": app.decision, "notice": "Recorded as the decision of the competent authority."}


@router.post("/{application_id}/clarification")
def clarification(application_id: int, body: ClarifyBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    engine.request_clarification(db, application_id, user, body.question)
    db.commit()
    return {"ok": True}


@router.get("/{application_id}/allowed-actions")
def allowed(application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    app = db.query(Application).options(
        joinedload(Application.current_stage),
        joinedload(Application.template).joinedload(WorkflowTemplate.stages),
    ).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    return {"actions": engine.allowed_actions(db, app, user)}


@router.get("/{application_id}/history")
def history(application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    rows = (
        db.query(ApplicationStageHistory)
        .filter(ApplicationStageHistory.application_id == application_id)
        .order_by(ApplicationStageHistory.created_at.asc())
        .all()
    )
    return [
        {
            "from_stage": h.from_stage,
            "to_stage": h.to_stage,
            "action": h.action,
            "actor_role": h.actor_role,
            "reason": h.reason,
            "created_at": h.created_at.isoformat(),
        }
        for h in rows
    ]


class CreateAppBody(BaseModel):
    institution_id: int | None = None
    application_type: str = "Extension"


@router.post("")
def create_application(body: CreateAppBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    if user.role.code != "institution_user":
        raise HTTPException(403, "Only institutions may submit applications in the portal")
    inst_id = user.institution_id
    if not inst_id:
        raise HTTPException(400, "User is not linked to an institution")
    inst = db.get(Institution, inst_id)
    count = db.query(Application).count() + 1
    app = Application(
        app_id=f"APP-2026-{count:04d}",
        institution_id=inst.id,
        application_type=body.application_type,
        template_id=1,
        status="open",
        region_id=inst.region_id,
        submitted_at=clock.now(),
        last_updated_at=clock.now(),
        simulated=True,
    )
    tpl = engine.template_for_type(db, body.application_type)
    app.template_id = tpl.id
    db.add(app)
    db.flush()
    engine.start(db, app, user)
    db.commit()
    return {"ok": True, "id": app.id, "app_id": app.app_id, "template": tpl.code}

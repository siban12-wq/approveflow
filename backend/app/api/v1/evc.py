from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Application, EvcMember, EvcVisit, User
from app.services.audit import write_audit

router = APIRouter()


@router.get("/queue")
def queue(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    visits = db.query(EvcVisit).all()
    apps = {a.id: a for a in db.query(Application).options(joinedload(Application.institution), joinedload(Application.current_stage)).all()}
    out = []
    for v in visits:
        app = apps.get(v.application_id)
        if not app:
            continue
        if user.role.code == "institution_user" and app.institution_id != user.institution_id:
            continue
        days = clock.days_since(v.eligible_since)
        out.append(
            {
                "id": v.id,
                "application_id": app.id,
                "app_id": app.app_id,
                "institution": app.institution.name,
                "status": v.status,
                "priority_new": app.institution.is_new,
                "days_since_eligible": days,
                "scheduling_deadline": v.scheduling_deadline.isoformat(),
                "scheduled_at": v.scheduled_at.isoformat() if v.scheduled_at else None,
                "venue": v.venue,
                "recommendation": v.recommendation,
            }
        )
    out.sort(key=lambda r: (not r["priority_new"], r["days_since_eligible"] * -1))
    return out


class ScheduleBody(BaseModel):
    scheduled_at: datetime
    venue: str
    member_ids: list[int] = []


@router.post("/{visit_id}/schedule")
def schedule(visit_id: int, body: ScheduleBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    visit = db.get(EvcVisit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    # Conflict: same member already booked at that time
    for mid in body.member_ids:
        clash = (
            db.query(EvcMember)
            .join(EvcVisit, EvcMember.visit_id == EvcVisit.id)
            .filter(EvcMember.user_id == mid, EvcVisit.scheduled_at == body.scheduled_at, EvcVisit.id != visit.id)
            .first()
        )
        if clash:
            raise HTTPException(409, "Committee member is double-booked at that time.")
    visit.scheduled_at = body.scheduled_at
    visit.venue = body.venue
    visit.status = "Scheduled"
    db.query(EvcMember).filter(EvcMember.visit_id == visit.id).delete()
    for mid in body.member_ids:
        db.add(EvcMember(visit_id=visit.id, user_id=mid))
    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.full_name,
        action="evc.schedule",
        entity_type="evc_visit",
        entity_id=visit.id,
        new_value=body.scheduled_at.isoformat(),
    )
    db.commit()
    return {"ok": True}


class ReportBody(BaseModel):
    recommendation: str
    notes: str | None = None


@router.post("/{visit_id}/report")
def report(visit_id: int, body: ReportBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    visit = db.get(EvcVisit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    if user.role.code not in {"committee_member", "super_admin", "regional_officer"}:
        raise HTTPException(403, "Only committee members may file a visit recommendation")
    visit.recommendation = body.recommendation
    visit.status = "Report Submitted"
    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.full_name,
        action="evc.report",
        entity_type="evc_visit",
        entity_id=visit.id,
        reason="Recommendation only — not a decision.",
        new_value=body.recommendation[:200],
    )
    db.commit()
    return {"ok": True, "notice": "Recommendation recorded. This is not a statutory decision."}

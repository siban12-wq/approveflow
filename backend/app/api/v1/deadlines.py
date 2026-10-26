"""API endpoints for the One Unified Deadline Engine.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.entities import Deadline, Institution, User
from app.services.deadline_engine import deadline_engine

router = APIRouter()


class DeadlineActionBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


def _serialize_deadline(d: Deadline, now) -> dict:
    aware_due = clock.aware(d.due_date)
    days_left = (aware_due.date() - now.date()).days if aware_due else 0
    return {
        "id": d.id,
        "deadline_code": d.deadline_code,
        "deadline_type": d.deadline_type,
        "linked_entity_type": d.linked_entity_type,
        "linked_entity_id": d.linked_entity_id,
        "institution_id": d.institution_id,
        "institution_name": d.institution.name if d.institution else None,
        "application_id": d.application_id,
        "responsible_user": d.responsible_user.full_name if d.responsible_user else None,
        "responsible_role": d.responsible_role,
        "title": d.title,
        "start_date": d.start_date.isoformat() if d.start_date else None,
        "due_date": d.due_date.isoformat() if d.due_date else None,
        "status": d.status,
        "days_left": days_left,
        "is_overdue": days_left < 0 and d.status not in {"completed", "verified"},
        "is_due_soon": 0 <= days_left <= 7 and d.status not in {"completed", "verified"},
        "escalation_level": d.escalation_level,
        "pause_reason": d.pause_reason,
        "completed_at": d.completed_at.isoformat() if d.completed_at else None,
        "verified_at": d.verified_at.isoformat() if d.verified_at else None,
    }


@router.get("")
def list_deadlines(
    deadline_type: str | None = None,
    status: str | None = None,
    institution_id: int | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 30,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    query = db.query(Deadline).options(
        joinedload(Deadline.institution),
        joinedload(Deadline.responsible_user),
    )

    if user.role.code == "institution_user":
        query = query.filter(Deadline.institution_id == user.institution_id)
    elif institution_id:
        query = query.filter(Deadline.institution_id == institution_id)

    if deadline_type:
        query = query.filter(Deadline.deadline_type == deadline_type)
    if status:
        query = query.filter(Deadline.status == status)
    if q:
        query = query.filter(Deadline.title.ilike(f"%{q}%"))

    total = query.count()
    rows = query.order_by(Deadline.due_date.asc()).offset((page - 1) * page_size).limit(page_size).all()
    now = clock.now()

    return {
        "total": total,
        "page": page,
        "items": [_serialize_deadline(d, now) for d in rows],
    }


@router.get("/summary")
def deadline_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    query = db.query(Deadline)
    if user.role.code == "institution_user":
        query = query.filter(Deadline.institution_id == user.institution_id)

    all_dls = query.all()
    now = clock.now()

    summary = {
        "total_active": 0,
        "overdue": 0,
        "due_soon": 0,
        "paused": 0,
        "completed": 0,
        "by_type": {
            "APPLICATION_SLA": 0,
            "EVC_SCHEDULING": 0,
            "UNDERTAKING": 0,
            "DOCUMENT_EXPIRY": 0,
        },
    }

    for d in all_dls:
        if d.status in {"completed", "verified"}:
            summary["completed"] += 1
            continue
        if d.status == "paused":
            summary["paused"] += 1
            continue

        summary["total_active"] += 1
        aware_due = clock.aware(d.due_date)
        days_left = (aware_due.date() - now.date()).days if aware_due else 0

        if days_left < 0:
            summary["overdue"] += 1
        elif days_left <= 7:
            summary["due_soon"] += 1

        if d.deadline_type in summary["by_type"]:
            summary["by_type"][d.deadline_type] += 1

    return summary


@router.post("/sync")
def trigger_sync(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin", "bureau_officer")),
) -> dict:
    count = deadline_engine.sync_all(db)
    return {"ok": True, "synchronized_count": count}


@router.post("/{deadline_id}/pause")
def pause(
    deadline_id: int,
    body: DeadlineActionBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin", "bureau_officer")),
) -> dict:
    try:
        dl = deadline_engine.pause_deadline(db, deadline_id, body.reason, user)
        return {"ok": True, "status": dl.status}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{deadline_id}/resume")
def resume(
    deadline_id: int,
    body: DeadlineActionBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin", "bureau_officer")),
) -> dict:
    try:
        dl = deadline_engine.resume_deadline(db, deadline_id, body.reason, user)
        return {"ok": True, "status": dl.status}
    except ValueError as e:
        raise HTTPException(404, str(e))

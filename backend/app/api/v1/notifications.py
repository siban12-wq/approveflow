from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Escalation, EscalationRule, Notification, User
from app.services.notifications import notification_service

router = APIRouter()


@router.get("/escalations")
def list_escalations(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    q = db.query(Escalation)
    if user.role.code == "regional_officer" and user.region_id:
        q = q.filter(Escalation.region_id == user.region_id)
    rows = q.order_by(Escalation.triggered_at.desc()).limit(200).all()
    return [
        {
            "id": e.id,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "level": e.level,
            "triggered_at": e.triggered_at.isoformat(),
            "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
            "resolution_note": e.resolution_note,
            "escalated_to_user_id": e.escalated_to_user_id,
        }
        for e in rows
    ]


@router.get("")
def list_notes(
    entity_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    unread: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    q = db.query(Notification).filter(Notification.recipient_id == user.id)
    if entity_type:
        q = q.filter(Notification.entity_type == entity_type)
    if severity:
        q = q.filter(Notification.severity == severity)
    if status:
        q = q.filter(Notification.status == status)
    if unread:
        q = q.filter(Notification.read_at.is_(None))
    rows = q.order_by(Notification.created_at.desc()).limit(200).all()
    unread_count = db.query(Notification).filter(Notification.recipient_id == user.id, Notification.read_at.is_(None)).count()
    return {
        "unread": unread_count,
        "items": [
            {
                "id": n.id,
                "entity_type": n.entity_type,
                "entity_id": n.entity_id,
                "severity": n.severity,
                "title": n.title,
                "body": n.body,
                "status": n.status,
                "level": n.level,
                "created_at": n.created_at.isoformat(),
                "snoozed_until": n.snoozed_until.isoformat() if n.snoozed_until else None,
            }
            for n in rows
        ],
    }


@router.post("/{note_id}/read")
def mark_read(note_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    note = db.get(Notification, note_id)
    if not note or note.recipient_id != user.id:
        raise HTTPException(404, "Notification not found")
    notification_service.mark_read(db, note)
    db.commit()
    return {"ok": True}


@router.post("/{note_id}/acknowledge")
def ack(note_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    note = db.get(Notification, note_id)
    if not note or note.recipient_id != user.id:
        raise HTTPException(404, "Notification not found")
    notification_service.acknowledge(db, note, user)
    db.commit()
    return {"ok": True}


class SnoozeBody(BaseModel):
    days: int = 1
    reason: str = Field(min_length=8)


@router.post("/{note_id}/snooze")
def snooze(note_id: int, body: SnoozeBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    note = db.get(Notification, note_id)
    if not note or note.recipient_id != user.id:
        raise HTTPException(404, "Notification not found")
    next_thr = None
    if note.severity == "CRITICAL":
        rule = (
            db.query(EscalationRule)
            .filter(EscalationRule.entity_type == note.entity_type, EscalationRule.level == (note.level or 0) + 1)
            .first()
        )
        if rule:
            next_thr = rule.threshold_days_overdue
    try:
        notification_service.snooze(db, note, user, body.days, body.reason, next_thr)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    db.commit()
    return {"ok": True, "until": note.snoozed_until.isoformat() if note.snoozed_until else None}


@router.get("/stream")
def stream(user: User = Depends(get_current_user)):
    """Simple SSE heartbeat. The client also polls; this keeps the bell live in demo."""

    def gen():
        yield "event: ping\ndata: {\"ok\": true}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/escalations/{entity_type}/{entity_id}")
def escalation_timeline(entity_type: str, entity_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    rows = (
        db.query(Escalation)
        .filter(Escalation.entity_type == entity_type.upper(), Escalation.entity_id == entity_id)
        .order_by(Escalation.level.asc())
        .all()
    )
    return {
        "ladder": [
            {"level": 0, "label": "Responsible officer / institution"},
            {"level": 1, "label": "Regional Officer"},
            {"level": 2, "label": "Bureau Officer"},
            {"level": 3, "label": "Designated senior authority"},
        ],
        "events": [
            {
                "level": e.level,
                "triggered_at": e.triggered_at.isoformat(),
                "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
                "note": e.resolution_note,
                "escalated_to_user_id": e.escalated_to_user_id,
            }
            for e in rows
        ],
    }

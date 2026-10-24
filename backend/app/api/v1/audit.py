from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.entities import AuditLog, User

router = APIRouter()


@router.get("")
def query_audit(
    q: str | None = None,
    action: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    query = db.query(AuditLog)
    if q:
        like = f"%{q}%"
        query = query.filter(AuditLog.entity_id.ilike(like) | AuditLog.action.ilike(like))
    if action:
        query = query.filter(AuditLog.action == action)
    rows = query.order_by(AuditLog.id.desc()).limit(400).all()
    return {
        "items": [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "actor_role": r.actor_role,
                "actor_label": r.actor_label,
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "old_value": r.old_value,
                "new_value": r.new_value,
                "reason": r.reason,
                "row_hash": r.row_hash[:12],
            }
            for r in rows
        ]
    }


@router.put("/{audit_id}")
def forbid_update(audit_id: int) -> None:
    raise HTTPException(405, "Audit rows are immutable.")


@router.delete("/{audit_id}")
def forbid_delete(audit_id: int) -> None:
    raise HTTPException(405, "Audit rows are immutable.")

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.models.entities import AuditLog


def _hash_row(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_audit(
    db: Session,
    *,
    actor_id: int | None,
    actor_role: str,
    actor_label: str,
    action: str,
    entity_type: str,
    entity_id: str | int,
    old_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
    ip: str | None = None,
) -> AuditLog:
    """Append-only audit. Callers must never update or delete existing rows."""
    last = db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1)).scalar_one_or_none()
    prev_hash = last.row_hash if last else "genesis"
    payload = {
        "timestamp": clock.now().isoformat(),
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
        "prev_hash": prev_hash,
    }
    row = AuditLog(
        timestamp=clock.now(),
        actor_id=actor_id,
        actor_role=actor_role,
        actor_label=actor_label,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        ip=ip,
        prev_hash=prev_hash,
        row_hash=_hash_row(payload),
    )
    db.add(row)
    db.flush()
    return row

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.models.entities import Notification, User
from app.services.audit import write_audit
from app.services.email import get_email_provider


def render_template(text: str, ctx: dict[str, str]) -> str:
    out = text
    for key, value in ctx.items():
        out = out.replace("{" + key + "}", str(value))
    return out


class NotificationService:
    def send(
        self,
        db: Session,
        *,
        recipient: User,
        entity_type: str,
        entity_id: int,
        rule_id: int | None,
        level: int,
        severity: str,
        title: str,
        body: str,
        date_bucket: str,
        channel: str = "in_app",
        email: bool = False,
    ) -> Notification | None:
        key = f"{rule_id}:{entity_type}:{entity_id}:{level}:{recipient.id}:{date_bucket}"
        row = Notification(
            recipient_id=recipient.id,
            entity_type=entity_type,
            entity_id=entity_id,
            rule_id=rule_id,
            level=level,
            severity=severity,
            title=title,
            body=body,
            status="queued",
            channel=channel,
            created_at=clock.now(),
            dedupe_key=key,
        )
        try:
            with db.begin_nested():
                db.add(row)
                db.flush()
        except IntegrityError:
            return None

        if email:
            try:
                get_email_provider().send(recipient.email, title, body)
                row.status = "sent"
            except Exception:  # noqa: BLE001 — delivery must not crash the job
                row.status = "failed"
        else:
            row.status = "sent"

        write_audit(
            db,
            actor_id=None,
            actor_role="SYSTEM",
            actor_label="SYSTEM",
            action="notification.send",
            entity_type=entity_type,
            entity_id=entity_id,
            new_value=title,
        )
        return row

    def mark_read(self, db: Session, note: Notification) -> Notification:
        note.read_at = clock.now()
        if note.status in {"queued", "sent"}:
            note.status = "read"
        return note

    def acknowledge(self, db: Session, note: Notification, user: User) -> Notification:
        note.acknowledged_at = clock.now()
        note.status = "acknowledged"
        write_audit(
            db,
            actor_id=user.id,
            actor_role=user.role.code,
            actor_label=user.full_name,
            action="notification.acknowledge",
            entity_type="notification",
            entity_id=note.id,
        )
        return note

    def snooze(
        self,
        db: Session,
        note: Notification,
        user: User,
        days: int,
        reason: str,
        next_escalation_days: int | None,
    ) -> Notification:
        if len(reason.strip()) < 8:
            raise ValueError("Snooze requires a reason of at least 8 characters.")
        until = clock.now() + timedelta(days=days)
        # Critical overdue items cannot be snoozed past the next escalation threshold.
        if note.severity == "CRITICAL" and next_escalation_days is not None:
            cap = clock.now() + timedelta(days=max(0, next_escalation_days - 1))
            if until > cap:
                until = cap
        note.snoozed_until = until
        note.snooze_reason = reason
        note.status = "snoozed"
        write_audit(
            db,
            actor_id=user.id,
            actor_role=user.role.code,
            actor_label=user.full_name,
            action="notification.snooze",
            entity_type="notification",
            entity_id=note.id,
            reason=reason,
            new_value=until.isoformat(),
        )
        return note


notification_service = NotificationService()


def users_by_roles(db: Session, roles: list[str], region_id: int | None = None) -> list[User]:
    q = select(User).join(User.role).where(User.is_active.is_(True))
    if roles:
        from app.models.entities import Role

        q = q.where(Role.code.in_(roles))
    if region_id is not None:
        q = q.where((User.region_id == region_id) | (User.region_id.is_(None)))
    return list(db.execute(q).scalars().unique().all())

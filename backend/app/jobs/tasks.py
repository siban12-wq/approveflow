from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.models.entities import (
    AlertRule,
    Application,
    Document,
    Escalation,
    EscalationRule,
    JobRun,
    User,
)
from app.services.audit import write_audit
from app.services.notifications import notification_service, users_by_roles
from app.jobs.evaluator import days_between, evaluator


def _start_run(db: Session, name: str) -> JobRun:
    run = JobRun(name=name, started_at=clock.now(), items_checked=0, alerts_created=0)
    db.add(run)
    db.flush()
    return run


def _finish(db: Session, run: JobRun, checked: int, created: int, errors: str | None = None) -> JobRun:
    run.finished_at = clock.now()
    run.items_checked = checked
    run.alerts_created = created
    run.errors = errors
    write_audit(
        db,
        actor_id=None,
        actor_role="SYSTEM",
        actor_label="SYSTEM",
        action=f"job.{run.name}",
        entity_type="job_run",
        entity_id=run.id,
        new_value=f"checked={checked} alerts={created}",
    )
    db.commit()
    return run


def sla_checker(db: Session) -> JobRun:
    run = _start_run(db, "sla_checker")
    now = clock.now()
    apps = db.execute(select(Application).where(Application.status.in_(["open", "returned"]))).scalars().all()
    n = 0
    for app in apps:
        if not app.sla_due_at or not app.stage_entered_at:
            continue
        due = clock.aware(app.sla_due_at)
        entered = clock.aware(app.stage_entered_at)
        if due is None or entered is None:
            continue
        sla_days = max((due - entered).days, 1)
        elapsed = (now - entered).total_seconds() / 86400
        if now >= due:
            app.sla_status = "overdue"
        elif elapsed >= sla_days * 0.8:
            app.sla_status = "approaching"
        else:
            app.sla_status = "on_track"
        n += 1
    created = 0
    rules = db.execute(select(AlertRule).where(AlertRule.is_active.is_(True), AlertRule.entity_type == "APPLICATION")).scalars().all()
    for rule in rules:
        created += evaluator.evaluate(db, rule)
    return _finish(db, run, n, created)


def evc_reminder_job(db: Session) -> JobRun:
    run = _start_run(db, "evc_reminder_job")
    rules = db.execute(select(AlertRule).where(AlertRule.is_active.is_(True), AlertRule.entity_type == "EVC")).scalars().all()
    created = 0
    for rule in rules:
        created += evaluator.evaluate(db, rule)
    return _finish(db, run, len(rules), created)


def undertaking_reminder_job(db: Session) -> JobRun:
    run = _start_run(db, "undertaking_reminder_job")
    rules = db.execute(select(AlertRule).where(AlertRule.is_active.is_(True), AlertRule.entity_type == "UNDERTAKING")).scalars().all()
    created = 0
    for rule in rules:
        created += evaluator.evaluate(db, rule)
    return _finish(db, run, len(rules), created)


def document_expiry_job(db: Session) -> JobRun:
    run = _start_run(db, "document_expiry_job")
    now = clock.now()
    docs = db.execute(select(Document)).scalars().all()
    for d in docs:
        left = days_between(d.expiry_date, now)
        if left < 0:
            d.status = "Expired"
        elif left <= 90 and d.status == "Valid":
            d.status = "Expiring Soon"
    created = 0
    rules = db.execute(select(AlertRule).where(AlertRule.is_active.is_(True), AlertRule.entity_type == "DOCUMENT")).scalars().all()
    for rule in rules:
        created += evaluator.evaluate(db, rule)
    return _finish(db, run, len(docs), created)


def escalation_job(db: Session) -> JobRun:
    """Moves overdue cases up exactly one configured level. Never decides the case."""
    run = _start_run(db, "escalation_job")
    now = clock.now()
    created = 0
    checked = 0
    apps = db.execute(
        select(Application).options(joinedload(Application.institution)).where(Application.status.in_(["open", "returned"]))
    ).scalars().unique().all()
    rules = list(db.execute(select(EscalationRule).where(EscalationRule.entity_type == "APPLICATION")).scalars().all())
    rules.sort(key=lambda r: r.level)
    for app in apps:
        checked += 1
        if not app.sla_due_at:
            continue
        overdue = -days_between(app.sla_due_at, now)
        if overdue < 1:
            continue
        existing = list(
            db.execute(
                select(Escalation).where(
                    Escalation.entity_type == "APPLICATION",
                    Escalation.entity_id == app.id,
                    Escalation.resolved_at.is_(None),
                )
            ).scalars().all()
        )
        current_level = max((e.level for e in existing), default=0)
        nxt = next((r for r in rules if r.level == current_level + 1 and overdue >= r.threshold_days_overdue), None)
        if not nxt:
            continue
        region_id = app.region_id if nxt.region_scoped else None
        officers = users_by_roles(db, [nxt.escalate_to_role], region_id)
        target = officers[0] if officers else None
        row = Escalation(
            entity_type="APPLICATION",
            entity_id=app.id,
            level=nxt.level,
            escalated_to_user_id=target.id if target else None,
            triggered_at=now,
            region_id=app.region_id,
        )
        db.add(row)
        db.flush()
        if target:
            note = notification_service.send(
                db,
                recipient=target,
                entity_type="APPLICATION",
                entity_id=app.id,
                rule_id=None,
                level=nxt.level,
                severity="CRITICAL",
                title=f"Escalation L{nxt.level}: {app.app_id}",
                body=f"{app.institution.name} is overdue at current stage. Alerts support officials; they never approve or reject.",
                date_bucket=f"esc-{nxt.level}",
            )
            if note:
                created += 1
        write_audit(
            db,
            actor_id=None,
            actor_role="SYSTEM",
            actor_label="SYSTEM",
            action="escalation.create",
            entity_type="application",
            entity_id=app.app_id,
            new_value=str(nxt.level),
        )
    # Auto-resolve when the underlying item is closed.
    open_esc = db.execute(select(Escalation).where(Escalation.resolved_at.is_(None))).scalars().all()
    closed_ids = {
        a.id
        for a in db.execute(select(Application).where(Application.status == "closed")).scalars().all()
    }
    for e in open_esc:
        if e.entity_type == "APPLICATION" and e.entity_id in closed_ids:
            e.resolved_at = now
            e.resolution_note = "Auto-resolved because the application was closed by a competent authority."
    return _finish(db, run, checked, created)


def digest_job(db: Session) -> JobRun:
    run = _start_run(db, "digest_job")
    now = clock.now()
    officers = db.execute(select(User).join(User.role).where(User.is_active.is_(True))).scalars().unique().all()
    created = 0
    from app.models.entities import Role

    for u in officers:
        if u.role.code == "institution_user":
            continue
        pending = db.execute(
            select(Application).where(Application.assigned_officer_id == u.id, Application.status.in_(["open", "returned"]))
        ).scalars().all()
        overdue = [a for a in pending if a.sla_status == "overdue"]
        body = (
            f"Daily digest for {u.full_name}: {len(pending)} open cases, {len(overdue)} overdue. "
            "Automated alerts support, but do not replace, decisions of the competent authority."
        )
        note = notification_service.send(
            db,
            recipient=u,
            entity_type="DIGEST",
            entity_id=u.id,
            rule_id=None,
            level=0,
            severity="INFO",
            title="Daily officer digest",
            body=body,
            date_bucket=now.date().isoformat(),
            email=True,
        )
        if note:
            created += 1
    return _finish(db, run, len(officers), created)


JOBS = {
    "sla_checker": sla_checker,
    "evc_reminder_job": evc_reminder_job,
    "undertaking_reminder_job": undertaking_reminder_job,
    "document_expiry_job": document_expiry_job,
    "escalation_job": escalation_job,
    "digest_job": digest_job,
}


def run_all(db: Session) -> list[JobRun]:
    return [fn(db) for fn in JOBS.values()]

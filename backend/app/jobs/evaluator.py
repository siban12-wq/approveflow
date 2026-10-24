"""Generic rule evaluator. Alerts never approve, reject, or decide a case."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.models.entities import (
    AlertRule,
    Application,
    Document,
    EvcVisit,
    NotificationTemplate,
    Undertaking,
    User,
)
from app.services.notifications import notification_service, render_template, users_by_roles


def days_between(due: datetime, now: datetime) -> int:
    due_aware = clock.aware(due) or due
    now_aware = clock.aware(now) or now
    return int((due_aware.date() - now_aware.date()).days)


class RuleEvaluator:
    def evaluate(self, db: Session, rule: AlertRule) -> int:
        created = 0
        now = clock.now()
        tpl = db.get(NotificationTemplate, rule.template_id) if rule.template_id else None
        entities = self._matching_entities(db, rule, now)
        for entity_type, entity_id, due, region_id, ctx in entities:
            days_left = days_between(due, now)
            ctx = {
                **ctx,
                "due_date": due.date().isoformat(),
                "days_left": str(max(days_left, 0)),
                "days_overdue": str(max(-days_left, 0)),
            }
            title = render_template(tpl.subject if tpl else rule.code, ctx)
            body = render_template(
                tpl.body
                if tpl
                else "Alert for {app_id}. Automated alerts support, but do not replace, decisions of the competent authority.",
                ctx,
            )
            bucket = self._bucket(rule, now, days_left)
            recipients = users_by_roles(db, rule.recipient_roles or [], region_id)
            # Institution-only: extra filter happens in _matching for institution users via roles.
            for rec in recipients:
                if rec.role.code == "institution_user" and ctx.get("_institution_id"):
                    if rec.institution_id != int(ctx["_institution_id"]):
                        continue
                note = notification_service.send(
                    db,
                    recipient=rec,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    rule_id=rule.id,
                    level=0,
                    severity=rule.severity,
                    title=title,
                    body=body,
                    date_bucket=bucket,
                    email=bool((rule.channels or {}).get("email")),
                )
                if note:
                    created += 1
        return created

    def _bucket(self, rule: AlertRule, now: datetime, days_left: int) -> str:
        if rule.trigger_type == "AFTER_DUE":
            # daily or weekly overdue buckets
            if rule.offset_days >= 7:
                iso = now.isocalendar()
                return f"{iso.year}-W{iso.week}"
            return now.date().isoformat()
        return f"{rule.code}:{now.date().isoformat()}" if rule.trigger_type == "AGEING" else f"{rule.code}:once"

    def _matching_entities(self, db: Session, rule: AlertRule, now: datetime) -> list[tuple]:
        out: list[tuple] = []
        if rule.entity_type == "APPLICATION":
            apps = db.execute(
                select(Application)
                .options(joinedload(Application.institution), joinedload(Application.current_stage), joinedload(Application.assigned_officer))
                .where(Application.status.in_(["open", "returned"]))
            ).scalars().unique().all()
            for app in apps:
                if not app.sla_due_at:
                    continue
                due = app.sla_due_at
                if self._matches(rule, due, now, app):
                    officer = app.assigned_officer.full_name if app.assigned_officer else "Unassigned"
                    out.append(
                        (
                            "APPLICATION",
                            app.id,
                            due,
                            app.region_id,
                            {
                                "institution": app.institution.name,
                                "app_id": app.app_id,
                                "stage": app.current_stage.name if app.current_stage else "",
                                "officer": officer,
                                "_institution_id": str(app.institution_id),
                            },
                        )
                    )
        elif rule.entity_type == "EVC":
            visits = db.execute(select(EvcVisit).options()).scalars().all()
            apps_by_id = {a.id: a for a in db.execute(select(Application).options(joinedload(Application.institution))).scalars().unique().all()}
            for v in visits:
                if v.status not in {"Pending Scheduling", "Scheduled"}:
                    continue
                due = v.scheduling_deadline if v.status == "Pending Scheduling" else (v.scheduled_at or v.scheduling_deadline)
                if self._matches(rule, due, now, None):
                    app = apps_by_id.get(v.application_id)
                    if not app:
                        continue
                    out.append(
                        (
                            "EVC",
                            v.id,
                            due,
                            app.region_id,
                            {
                                "institution": app.institution.name,
                                "app_id": app.app_id,
                                "stage": "EVC",
                                "officer": "EVC desk",
                                "_institution_id": str(app.institution_id),
                            },
                        )
                    )
        elif rule.entity_type == "UNDERTAKING":
            items = db.execute(select(Undertaking)).scalars().all()
            inst_cache: dict[int, str] = {}
            for u in items:
                if u.status in {"Accepted", "Closed"}:
                    continue
                if self._matches(rule, u.due_date, now, None):
                    name = inst_cache.get(u.institution_id) or ""
                    out.append(
                        (
                            "UNDERTAKING",
                            u.id,
                            u.due_date,
                            None,
                            {
                                "institution": name,
                                "app_id": f"UT-{u.id}",
                                "stage": u.category,
                                "officer": "Compliance desk",
                                "_institution_id": str(u.institution_id),
                            },
                        )
                    )
        elif rule.entity_type == "DOCUMENT":
            docs = db.execute(select(Document)).scalars().all()
            for d in docs:
                if self._matches(rule, d.expiry_date, now, None):
                    out.append(
                        (
                            "DOCUMENT",
                            d.id,
                            d.expiry_date,
                            None,
                            {
                                "institution": "",
                                "app_id": d.document_number,
                                "stage": d.doc_type,
                                "officer": "Document desk",
                                "_institution_id": str(d.institution_id),
                            },
                        )
                    )
        return out

    def _matches(self, rule: AlertRule, due: datetime, now: datetime, app: Application | None) -> bool:
        delta = days_between(due, now)
        if rule.trigger_type == "BEFORE_DUE":
            # offset_days is negative in seed (e.g. -7). Match exact remaining days.
            return delta == abs(rule.offset_days) or delta == -rule.offset_days
        if rule.trigger_type == "ON_DUE":
            return delta == 0
        if rule.trigger_type == "AFTER_DUE":
            overdue = -delta
            if overdue < 1:
                return False
            if rule.offset_days <= 1:
                return overdue >= 1
            return overdue >= rule.offset_days and (overdue - rule.offset_days) % max(rule.offset_days, 1) == 0
        if rule.trigger_type == "AGEING" and app and app.stage_entered_at:
            entered = clock.aware(app.stage_entered_at) or app.stage_entered_at
            elapsed = (now - entered).days
            sla = app.current_stage.sla_days if app.current_stage else 15
            if rule.severity == "WARNING":
                return sla > 0 and elapsed >= int(sla * 0.8) and elapsed < sla
            if rule.severity == "CRITICAL":
                return elapsed >= sla
        return False


evaluator = RuleEvaluator()

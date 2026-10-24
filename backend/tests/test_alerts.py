from datetime import timedelta

from sqlalchemy.orm import joinedload

from app.core.clock import clock
from app.jobs.evaluator import evaluator
from app.jobs.tasks import document_expiry_job, escalation_job, sla_checker
from app.models.entities import (
    AlertRule,
    Application,
    AuditLog,
    Document,
    Escalation,
    EscalationRule,
    Institution,
    Notification,
    NotificationTemplate,
    User,
    WorkflowTemplate,
)
from app.services.notifications import notification_service
from app.workflows.engine import WorkflowEngine
from tests.conftest import user_by_role


def _app_overdue(db) -> Application:
    inst = db.query(Institution).first()
    tpl = db.query(WorkflowTemplate).options(joinedload(WorkflowTemplate.stages)).filter_by(code="ONLY_SCRUTINY").one()
    stage = next(s for s in tpl.stages if s.stage_code == "SCRUTINY")
    app = Application(
        app_id="APP-ALERT-1",
        institution_id=inst.id,
        application_type="Closure",
        template_id=tpl.id,
        current_stage_id=stage.id,
        status="open",
        region_id=inst.region_id,
        submitted_at=clock.now() - timedelta(days=40),
        stage_entered_at=clock.now() - timedelta(days=20),
        sla_due_at=clock.now() - timedelta(days=5),
        sla_status="overdue",
        last_updated_at=clock.now(),
        assigned_officer_id=user_by_role(db, "regional_officer").id,
        simulated=True,
    )
    db.add(app)
    db.flush()
    return app


def _ensure_rules(db) -> None:
    if db.query(NotificationTemplate).count():
        return
    tpl = NotificationTemplate(code="T", subject="Alert {app_id}", body="Due {due_date} left {days_left} overdue {days_overdue}")
    db.add(tpl)
    db.flush()
    db.add(
        AlertRule(
            code="APP_SLA_BREACH",
            entity_type="APPLICATION",
            trigger_type="AGEING",
            offset_days=0,
            channels={"in_app": True},
            recipient_roles=["regional_officer"],
            severity="CRITICAL",
            template_id=tpl.id,
            is_active=True,
        )
    )
    db.add(EscalationRule(entity_type="APPLICATION", level=1, threshold_days_overdue=3, escalate_to_role="regional_officer", region_scoped=True))
    db.add(EscalationRule(entity_type="APPLICATION", level=2, threshold_days_overdue=10, escalate_to_role="bureau_officer", region_scoped=False))
    db.add(EscalationRule(entity_type="APPLICATION", level=3, threshold_days_overdue=20, escalate_to_role="super_admin", region_scoped=False))
    db.commit()


def test_idempotent_job(db):
    _ensure_rules(db)
    _app_overdue(db)
    db.commit()
    sla_checker(db)
    sla_checker(db)
    sla_checker(db)
    count = db.query(Notification).filter(Notification.entity_type == "APPLICATION").count()
    # Three runs must not multiply the same rule/entity/day bucket.
    first = count
    sla_checker(db)
    assert db.query(Notification).filter(Notification.entity_type == "APPLICATION").count() == first


def test_escalation_one_level(db):
    _ensure_rules(db)
    app = _app_overdue(db)
    db.commit()
    escalation_job(db)
    rows = db.query(Escalation).filter_by(entity_id=app.id).all()
    assert len(rows) == 1
    assert rows[0].level == 1
    escalation_job(db)
    rows = db.query(Escalation).filter_by(entity_id=app.id).all()
    assert len(rows) == 1  # still one until next threshold


def test_escalation_auto_resolve(db):
    _ensure_rules(db)
    app = _app_overdue(db)
    db.commit()
    escalation_job(db)
    app.status = "closed"
    db.commit()
    escalation_job(db)
    row = db.query(Escalation).filter_by(entity_id=app.id).one()
    assert row.resolved_at is not None


def test_institution_isolation(db):
    _ensure_rules(db)
    _app_overdue(db)
    db.commit()
    sla_checker(db)
    inst_user = user_by_role(db, "institution_user")
    other = db.query(Notification).filter(Notification.recipient_id == inst_user.id, Notification.entity_type == "APPLICATION").all()
    # Default SLA rule targets officers, not the institution.
    assert other == []


def test_notification_has_audit(db):
    _ensure_rules(db)
    _app_overdue(db)
    db.commit()
    sla_checker(db)
    notes = db.query(Notification).all()
    audits = db.query(AuditLog).filter(AuditLog.action == "notification.send").all()
    assert len(notes) == len(audits) or len(audits) >= len(notes)


def test_document_status_flip(db):
    inst = db.query(Institution).first()
    db.add(
        Document(
            institution_id=inst.id,
            doc_type="lease_deed",
            document_number="L-1",
            issue_date=clock.now() - timedelta(days=400),
            expiry_date=clock.now() - timedelta(days=1),
            status="Valid",
        )
    )
    db.commit()
    document_expiry_job(db)
    doc = db.query(Document).first()
    assert doc.status == "Expired"


def test_snooze_requires_reason(db):
    ro = user_by_role(db, "regional_officer")
    n = Notification(
        recipient_id=ro.id,
        entity_type="APPLICATION",
        entity_id=1,
        rule_id=None,
        level=0,
        severity="WARNING",
        title="t",
        body="b",
        status="sent",
        created_at=clock.now(),
        dedupe_key="unique-snooze-1",
    )
    db.add(n)
    db.flush()
    try:
        notification_service.snooze(db, n, ro, 3, "no", None)
        assert False, "should require reason"
    except ValueError:
        pass
    notification_service.snooze(db, n, ro, 3, "Waiting for annexure from the college", None)
    assert n.status == "snoozed"

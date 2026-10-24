from datetime import timedelta

import pytest
from sqlalchemy.orm import joinedload

from app.core.clock import clock
from app.core.errors import ForbiddenActionError, IllegalTransitionError
from app.models.entities import Application, AuditLog, Deficiency, WorkflowTemplate
from app.workflows.engine import WorkflowEngine, TYPE_TO_TEMPLATE
from tests.conftest import user_by_role


def _make_app(db, atype: str = "Extension") -> Application:
    from app.models.entities import Institution

    inst = db.query(Institution).first()
    tpl = db.query(WorkflowTemplate).options(joinedload(WorkflowTemplate.stages)).filter_by(code=TYPE_TO_TEMPLATE[atype]).one()
    n = db.query(Application).count() + 1
    app = Application(
        app_id=f"APP-T-{n:04d}",
        institution_id=inst.id,
        application_type=atype,
        template_id=tpl.id,
        status="open",
        region_id=inst.region_id,
        submitted_at=clock.now(),
        last_updated_at=clock.now(),
        simulated=True,
    )
    app.template = tpl
    db.add(app)
    db.flush()
    return app


def _stage_codes(app: Application) -> list[str]:
    return [s.stage_code for s in sorted(app.template.stages, key=lambda s: s.order_no)]


def test_start_all_templates(db):
    eng = WorkflowEngine()
    inst_user = user_by_role(db, "institution_user")
    for atype, code in TYPE_TO_TEMPLATE.items():
        app = _make_app(db, atype)
        eng.start(db, app, inst_user)
        db.commit()
        db.refresh(app)
        assert app.template.code == code
        assert app.current_stage.stage_code != "SUBMITTED"
        assert app.sla_due_at is not None
        assert app.decision is None


def test_legal_forward_scrutiny_evc(db):
    eng = WorkflowEngine()
    inst = user_by_role(db, "institution_user")
    ro = user_by_role(db, "regional_officer")
    app = _make_app(db, "Extension")
    eng.start(db, app, inst)
    db.commit()
    assert app.current_stage.stage_code == "SCRUTINY"
    eng.forward(db, app.id, ro, remarks="Scrutiny complete, files in order.")
    db.commit()
    db.refresh(app)
    assert app.current_stage.stage_code == "EVC_QUEUE"


def test_wrong_role_cannot_forward(db):
    eng = WorkflowEngine()
    inst = user_by_role(db, "institution_user")
    cm = user_by_role(db, "committee_member")
    app = _make_app(db, "Extension")
    eng.start(db, app, inst)
    db.commit()
    with pytest.raises(ForbiddenActionError):
        eng.forward(db, app.id, cm, remarks="Not my desk.")


def test_return_without_reason_fails(db):
    eng = WorkflowEngine()
    inst = user_by_role(db, "institution_user")
    ro = user_by_role(db, "regional_officer")
    app = _make_app(db, "Extension")
    eng.start(db, app, inst)
    db.commit()
    with pytest.raises(IllegalTransitionError):
        eng.return_back(db, app.id, ro, reason="too short")


def test_return_creates_deficiency_and_history(db):
    eng = WorkflowEngine()
    inst = user_by_role(db, "institution_user")
    ro = user_by_role(db, "regional_officer")
    app = _make_app(db, "Extension")
    eng.start(db, app, inst)
    db.commit()
    reason = "Land documents are incomplete and must be reissued by the competent sub-registrar."
    eng.return_back(db, app.id, ro, reason=reason)
    db.commit()
    defs = db.query(Deficiency).filter_by(application_id=app.id).all()
    assert len(defs) == 1
    assert defs[0].status == "Open"
    with pytest.raises(IllegalTransitionError):
        eng.forward(db, app.id, ro, remarks="Trying to skip deficiency.")
    eng.institution_respond(db, app.id, inst, "Uploaded certified land records as requested.")
    db.commit()
    db.refresh(app)
    assert app.current_stage.stage_code == "SCRUTINY"


def test_double_forward_second_fails(db):
    eng = WorkflowEngine()
    inst = user_by_role(db, "institution_user")
    ro = user_by_role(db, "regional_officer")
    app = _make_app(db, "Closure")
    eng.start(db, app, inst)
    db.commit()
    eng.forward(db, app.id, ro, remarks="Scrutiny complete for closure.")
    db.commit()
    with pytest.raises(IllegalTransitionError):
        eng.forward(db, app.id, ro, remarks="Second forward must fail at decision pending.")


def test_sla_recalculated_on_entry(db):
    eng = WorkflowEngine()
    inst = user_by_role(db, "institution_user")
    ro = user_by_role(db, "regional_officer")
    app = _make_app(db, "Extension")
    eng.start(db, app, inst)
    first_due = app.sla_due_at
    clock.advance_days(2)
    eng.forward(db, app.id, ro, remarks="Moving after two days of scrutiny.")
    db.commit()
    assert app.sla_due_at != first_due
    assert app.current_stage.stage_code == "EVC_QUEUE"


def test_audit_row_every_transition(db):
    eng = WorkflowEngine()
    inst = user_by_role(db, "institution_user")
    ro = user_by_role(db, "regional_officer")
    app = _make_app(db, "Extension")
    eng.start(db, app, inst)
    eng.forward(db, app.id, ro, remarks="Scrutiny signed off by officer.")
    db.commit()
    rows = db.query(AuditLog).filter(AuditLog.entity_id == app.app_id).all()
    assert len(rows) >= 2


def test_no_auto_approve(db):
    """The engine never writes a decision without record_decision() from a human."""
    import inspect
    from app.workflows import engine as mod

    source = inspect.getsource(mod.WorkflowEngine)
    assert "app.decision = \"approved\"" not in source
    assert "auto-approve" not in source.lower()
    eng = WorkflowEngine()
    inst = user_by_role(db, "institution_user")
    ro = user_by_role(db, "regional_officer")
    bureau = user_by_role(db, "bureau_officer")
    app = _make_app(db, "Closure")
    eng.start(db, app, inst)
    eng.forward(db, app.id, ro, remarks="Scrutiny complete, send to decision.")
    db.commit()
    assert app.decision is None
    with pytest.raises(ForbiddenActionError):
        eng.record_decision(db, app.id, ro, "approved", "ORD-1")
    eng.record_decision(db, app.id, bureau, "approved", "ORD-2026-1")
    db.commit()
    assert app.decision == "approved"
    assert app.status == "closed"


def test_illegal_skip_decision_pending(db):
    eng = WorkflowEngine()
    inst = user_by_role(db, "institution_user")
    ro = user_by_role(db, "regional_officer")
    app = _make_app(db, "Closure")
    eng.start(db, app, inst)
    eng.forward(db, app.id, ro, remarks="Scrutiny complete toward decision.")
    db.commit()
    with pytest.raises(IllegalTransitionError):
        eng.forward(db, app.id, ro, remarks="Cannot skip human decision.")

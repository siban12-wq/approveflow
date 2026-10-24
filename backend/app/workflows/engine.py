"""Workflow routing engine.

Humans make every statutory decision. This engine only:
- selects a template
- validates legal transitions
- records history + audit
- notifies the next owner
It never computes approve/reject.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.core.errors import ForbiddenActionError, IllegalTransitionError, NotFoundError
from app.models.entities import (
    Application,
    ApplicationStageHistory,
    Deficiency,
    User,
    WorkflowStage,
    WorkflowTemplate,
)
from app.services.audit import write_audit
from app.services.notifications import notification_service

# Application type → template code. Super Admin can still reassign a template.
TYPE_TO_TEMPLATE = {
    "New": "SCRUTINY_EVC_SAC_SHC",
    "Extension": "SCRUTINY_EVC",
    "Closure": "ONLY_SCRUTINY",
    "Increase in Intake": "EVC_SAC_SHC",
    "New Campus": "ONLY_EVC",
}

COMPETENT_AUTHORITY_ROLES = {"super_admin", "bureau_officer"}
DECISION_VALUES = {"approved", "rejected", "returned_with_conditions"}

# Stage codes that may be auto-advanced only after an authorised human action
# (forward / record recommendation). Never skip Decision Pending.
HUMAN_DECISION_STAGE = "DECISION_PENDING"


class WorkflowEngine:
    def lock_application(self, db: Session, application_id: int) -> Application:
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                joinedload(Application.current_stage),
                joinedload(Application.template).joinedload(WorkflowTemplate.stages),
                joinedload(Application.assigned_officer),
                joinedload(Application.institution),
            )
            .with_for_update()
        )
        app = db.execute(stmt).unique().scalar_one_or_none()
        if not app:
            raise NotFoundError("Application not found.")
        return app

    def template_for_type(self, db: Session, application_type: str) -> WorkflowTemplate:
        code = TYPE_TO_TEMPLATE.get(application_type, "SCRUTINY_EVC_SAC_SHC")
        tpl = db.execute(
            select(WorkflowTemplate)
            .options(joinedload(WorkflowTemplate.stages))
            .where(WorkflowTemplate.code == code, WorkflowTemplate.is_active.is_(True))
        ).unique().scalar_one_or_none()
        if not tpl:
            raise IllegalTransitionError(f"No active workflow template for type {application_type}.")
        return tpl

    def start(self, db: Session, application: Application, actor: User | None = None) -> Application:
        tpl = application.template or self.template_for_type(db, application.application_type)
        stages = sorted(tpl.stages, key=lambda s: s.order_no)
        if not stages:
            raise IllegalTransitionError("Workflow template has no stages.")
        # Submission is a human action that completes SUBMITTED and enters the first processing stage.
        first = stages[0]
        if first.stage_code == "SUBMITTED" and len(stages) > 1:
            self._history(db, application, None, "SUBMITTED", "start", actor, "Institution submission", None)
            first = stages[1]
        now = clock.now()
        application.template_id = tpl.id
        application.current_stage_id = first.id
        application.stage_entered_at = now
        application.sla_due_at = now + timedelta(days=first.sla_days)
        application.sla_status = "on_track"
        application.status = "open"
        application.last_updated_at = now
        officer = self._assign_next_owner(db, application, first)
        if officer:
            application.assigned_officer_id = officer.id
        self._history(db, application, None, first.stage_code, "start", actor, None, None)
        write_audit(
            db,
            actor_id=actor.id if actor else None,
            actor_role=actor.role.code if actor else "SYSTEM",
            actor_label=actor.full_name if actor else "SYSTEM",
            action="application.start",
            entity_type="application",
            entity_id=application.app_id,
            new_value=first.stage_code,
        )
        return application

    def forward(self, db: Session, application_id: int, actor: User, remarks: str | None = None) -> Application:
        app = self.lock_application(db, application_id)
        stage = app.current_stage
        if not stage:
            raise IllegalTransitionError("Application has no current stage.")
        if stage.stage_code == HUMAN_DECISION_STAGE:
            raise IllegalTransitionError(
                "Decision Pending cannot be forwarded. A competent authority must record a human decision."
            )
        if self._open_deficiencies(db, app.id):
            raise IllegalTransitionError("Open deficiencies block forwarding. The institution must respond first.")
        self._assert_role(actor, stage)
        if stage.requires_remarks and not (remarks and len(remarks.strip()) >= 8):
            raise IllegalTransitionError("This stage requires remarks of at least 8 characters before forward.")
        nxt = self._next_stage(app.template, stage)
        if not nxt:
            raise IllegalTransitionError("No next stage. Record a human decision to close the case.")
        old = stage.stage_code
        self._enter_stage(db, app, nxt, actor, "forward", remarks, old)
        return app

    def return_back(
        self,
        db: Session,
        application_id: int,
        actor: User,
        reason: str,
        target_stage_id: int | None = None,
    ) -> Application:
        if not reason or len(reason.strip()) < 15:
            raise IllegalTransitionError("Return requires a recorded reason of at least 15 characters.")
        app = self.lock_application(db, application_id)
        stage = app.current_stage
        if not stage:
            raise IllegalTransitionError("Application has no current stage.")
        self._assert_role(actor, stage)
        target = None
        if target_stage_id:
            target = next((s for s in app.template.stages if s.id == target_stage_id), None)
            if not target:
                raise IllegalTransitionError("Target stage is not part of this workflow template.")
            if target.order_no > stage.order_no:
                raise IllegalTransitionError("Cannot return forward. Pick the current or a previous stage.")
        else:
            target = self._previous_stage(app.template, stage)
        now = clock.now()
        defn = Deficiency(
            application_id=app.id,
            raised_by=actor.id,
            stage_id=stage.id,
            description=reason.strip(),
            status="Open",
            response_due_at=now + timedelta(days=15),
        )
        db.add(defn)
        old = stage.stage_code
        if target is None or target.stage_code == "SUBMITTED":
            app.status = "returned"
            # Remain conceptually with the institution for response.
            submitted = next((s for s in app.template.stages if s.stage_code == "SUBMITTED"), stage)
            self._enter_stage(db, app, submitted, actor, "return", reason, old)
        else:
            app.status = "returned"
            self._enter_stage(db, app, target, actor, "return", reason, old)
        self._notify_institution(db, app, "Application returned for deficiency", reason)
        return app

    def institution_respond(
        self,
        db: Session,
        application_id: int,
        actor: User,
        response: str,
        docs: list[str] | None = None,
    ) -> Application:
        if actor.role.code != "institution_user":
            raise ForbiddenActionError("Only the institution user may respond to a deficiency.")
        if actor.institution_id is None:
            raise ForbiddenActionError("Institution user is not linked to an institution.")
        app = self.lock_application(db, application_id)
        if actor.institution_id != app.institution_id:
            raise ForbiddenActionError("You may only respond on your own institution's applications.")
        open_defs = self._open_deficiencies(db, app.id)
        if not open_defs:
            raise IllegalTransitionError("There is no open deficiency to respond to.")
        if not response or len(response.strip()) < 8:
            raise IllegalTransitionError("A response of at least 8 characters is required.")
        now = clock.now()
        raising_stage_id = open_defs[0].stage_id
        for d in open_defs:
            d.status = "Responded"
            d.response_text = response.strip()
            d.responded_at = now
        raising = db.get(WorkflowStage, raising_stage_id)
        if raising is None:
            raise IllegalTransitionError("The stage that raised the deficiency no longer exists.")
        old = app.current_stage.stage_code if app.current_stage else None
        app.status = "open"
        label_reason = response.strip()
        if raising.stage_code == "SCRUTINY":
            label_reason = f"[Re-scrutiny] {label_reason}"
        self._enter_stage(db, app, raising, actor, "respond", label_reason, old)
        return app

    def reassign(self, db: Session, application_id: int, actor: User, new_officer_id: int, reason: str) -> Application:
        if actor.role.code not in {"super_admin", "bureau_officer", "regional_officer"}:
            raise ForbiddenActionError("You are not allowed to reassign applications.")
        if not reason or len(reason.strip()) < 8:
            raise IllegalTransitionError("Reassignment requires a reason.")
        app = self.lock_application(db, application_id)
        officer = db.get(User, new_officer_id)
        if not officer:
            raise NotFoundError("Officer not found.")
        old = str(app.assigned_officer_id)
        app.assigned_officer_id = officer.id
        app.last_updated_at = clock.now()
        self._history(
            db,
            app,
            app.current_stage.stage_code if app.current_stage else None,
            app.current_stage.stage_code if app.current_stage else "",
            "reassign",
            actor,
            reason,
            0,
        )
        write_audit(
            db,
            actor_id=actor.id,
            actor_role=actor.role.code,
            actor_label=actor.full_name,
            action="application.reassign",
            entity_type="application",
            entity_id=app.app_id,
            old_value=old,
            new_value=str(officer.id),
            reason=reason,
        )
        notification_service.send(
            db,
            recipient=officer,
            entity_type="APPLICATION",
            entity_id=app.id,
            rule_id=None,
            level=0,
            severity="INFO",
            title=f"Assigned {app.app_id}",
            body=f"You are the new owner of {app.app_id}. Reason: {reason}",
            date_bucket=clock.now().date().isoformat(),
        )
        return app

    def request_clarification(self, db: Session, application_id: int, actor: User, question: str) -> Application:
        if not question or len(question.strip()) < 10:
            raise IllegalTransitionError("Clarification request needs a question of at least 10 characters.")
        app = self.lock_application(db, application_id)
        if app.current_stage:
            self._assert_role(actor, app.current_stage)
        self._history(
            db,
            app,
            app.current_stage.stage_code if app.current_stage else None,
            app.current_stage.stage_code if app.current_stage else "",
            "clarification",
            actor,
            question,
            0,
        )
        write_audit(
            db,
            actor_id=actor.id,
            actor_role=actor.role.code,
            actor_label=actor.full_name,
            action="application.clarification",
            entity_type="application",
            entity_id=app.app_id,
            reason=question,
        )
        self._notify_institution(db, app, "Clarification requested", question)
        return app

    def record_decision(
        self,
        db: Session,
        application_id: int,
        actor: User,
        decision: str,
        order_ref: str,
    ) -> Application:
        """Records a human decision. The engine never computes or suggests the value."""
        if actor.role.code not in COMPETENT_AUTHORITY_ROLES:
            raise ForbiddenActionError("Only a competent authority may record a final decision.")
        decision_norm = (decision or "").strip().lower()
        if decision_norm not in DECISION_VALUES:
            raise IllegalTransitionError(
                "Decision must be provided by the competent authority: approved, rejected, or returned_with_conditions."
            )
        if not order_ref or len(order_ref.strip()) < 4:
            raise IllegalTransitionError("An order reference from the competent authority is required.")
        app = self.lock_application(db, application_id)
        stage = app.current_stage
        if not stage or stage.stage_code != HUMAN_DECISION_STAGE:
            raise IllegalTransitionError("A final decision may only be recorded at the Decision Pending stage.")
        closed = next((s for s in app.template.stages if s.stage_code == "CLOSED"), None)
        if not closed:
            raise IllegalTransitionError("Template is missing a Closed stage.")
        old = stage.stage_code
        app.decision = decision_norm
        app.decision_order_ref = order_ref.strip()
        app.status = "closed"
        self._enter_stage(db, app, closed, actor, "decision", f"{decision_norm} / {order_ref}", old)
        write_audit(
            db,
            actor_id=actor.id,
            actor_role=actor.role.code,
            actor_label=actor.full_name,
            action="application.decision",
            entity_type="application",
            entity_id=app.app_id,
            new_value=decision_norm,
            reason=order_ref,
        )
        return app

    def allowed_actions(self, db: Session, application: Application, actor: User) -> list[dict]:
        actions: list[dict] = []
        stage = application.current_stage
        role = actor.role.code
        if role == "institution_user":
            if application.institution_id != actor.institution_id:
                return []
            if self._open_deficiencies(db, application.id):
                actions.append({"code": "respond", "label": "Respond to deficiency"})
            return actions
        if not stage:
            return actions
        if role in (stage.allowed_roles or []) and application.status != "closed":
            if stage.stage_code not in {HUMAN_DECISION_STAGE, "CLOSED"}:
                actions.append({"code": "forward", "label": "Mark stage complete and forward"})
            actions.append({"code": "return", "label": "Return for deficiency"})
            actions.append({"code": "clarification", "label": "Request clarification"})
        if role in {"super_admin", "bureau_officer", "regional_officer"} and application.status != "closed":
            actions.append({"code": "assign", "label": "Reassign officer"})
        if role in COMPETENT_AUTHORITY_ROLES and stage.stage_code == HUMAN_DECISION_STAGE:
            actions.append(
                {
                    "code": "decision",
                    "label": "Record decision of competent authority",
                    "banner": "Human oversight required. This action records the decision of the competent authority.",
                }
            )
        return actions

    def _assert_role(self, actor: User, stage: WorkflowStage) -> None:
        allowed = stage.allowed_roles or []
        if actor.role.code not in allowed and actor.role.code != "super_admin":
            raise ForbiddenActionError(
                f"Role {actor.role.code} cannot act at stage {stage.name}. Allowed: {', '.join(allowed)}."
            )

    def _open_deficiencies(self, db: Session, application_id: int) -> list[Deficiency]:
        return list(
            db.execute(
                select(Deficiency).where(
                    Deficiency.application_id == application_id, Deficiency.status == "Open"
                )
            ).scalars().all()
        )

    def _next_stage(self, template: WorkflowTemplate, current: WorkflowStage) -> WorkflowStage | None:
        ordered = sorted(template.stages, key=lambda s: s.order_no)
        for s in ordered:
            if s.order_no > current.order_no:
                return s
        return None

    def _previous_stage(self, template: WorkflowTemplate, current: WorkflowStage) -> WorkflowStage | None:
        ordered = sorted(template.stages, key=lambda s: s.order_no)
        prev = None
        for s in ordered:
            if s.order_no >= current.order_no:
                break
            prev = s
        return prev

    def _enter_stage(
        self,
        db: Session,
        app: Application,
        new_stage: WorkflowStage,
        actor: User,
        action: str,
        reason: str | None,
        old_code: str | None,
    ) -> None:
        now = clock.now()
        duration = None
        if app.stage_entered_at:
            entered = clock.aware(app.stage_entered_at)
            duration = (now - entered).total_seconds() / 3600.0 if entered else None
        app.current_stage_id = new_stage.id
        app.current_stage = new_stage
        app.stage_entered_at = now
        app.sla_due_at = now + timedelta(days=new_stage.sla_days)
        app.last_updated_at = now
        if app.sla_due_at and now >= app.sla_due_at:
            app.sla_status = "overdue"
        else:
            app.sla_status = "on_track"
        owner = self._assign_next_owner(db, app, new_stage)
        if owner:
            app.assigned_officer_id = owner.id
        self._history(db, app, old_code, new_stage.stage_code, action, actor, reason, duration)
        write_audit(
            db,
            actor_id=actor.id,
            actor_role=actor.role.code,
            actor_label=actor.full_name,
            action=f"application.{action}",
            entity_type="application",
            entity_id=app.app_id,
            old_value=old_code,
            new_value=new_stage.stage_code,
            reason=reason,
        )
        if owner:
            notification_service.send(
                db,
                recipient=owner,
                entity_type="APPLICATION",
                entity_id=app.id,
                rule_id=None,
                level=0,
                severity="INFO",
                title=f"{app.app_id} is at {new_stage.name}",
                body=f"Routed by {actor.full_name}. Automation does not decide the case.",
                date_bucket=now.date().isoformat(),
            )

    def _assign_next_owner(self, db: Session, app: Application, stage: WorkflowStage) -> User | None:
        roles = stage.allowed_roles or []
        if not roles:
            return None
        stmt = (
            select(User)
            .join(User.role)
            .where(User.is_active.is_(True))
        )
        from app.models.entities import Role

        stmt = stmt.where(Role.code.in_(roles))
        if app.region_id and "regional_officer" in roles:
            stmt = stmt.where((User.region_id == app.region_id) | (User.region_id.is_(None)))
        stmt = stmt.order_by(User.open_case_count.asc(), User.id.asc())
        return db.execute(stmt).scalars().first()

    def _history(
        self,
        db: Session,
        app: Application,
        from_stage: str | None,
        to_stage: str,
        action: str,
        actor: User | None,
        reason: str | None,
        duration: float | None,
    ) -> None:
        db.add(
            ApplicationStageHistory(
                application_id=app.id,
                from_stage=from_stage,
                to_stage=to_stage,
                action=action,
                actor_id=actor.id if actor else None,
                actor_role=actor.role.code if actor else "SYSTEM",
                reason=reason,
                created_at=clock.now(),
                duration_in_stage_hours=duration,
            )
        )

    def _notify_institution(self, db: Session, app: Application, title: str, body: str) -> None:
        users = list(
            db.execute(select(User).where(User.institution_id == app.institution_id, User.is_active.is_(True)))
            .scalars()
            .all()
        )
        for u in users:
            notification_service.send(
                db,
                recipient=u,
                entity_type="APPLICATION",
                entity_id=app.id,
                rule_id=None,
                level=0,
                severity="WARNING",
                title=title,
                body=body,
                date_bucket=clock.now().date().isoformat(),
            )


engine = WorkflowEngine()

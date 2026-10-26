"""One Unified Deadline Engine.
Manages all 4 administrative time-bound commitments:
1. Application Stage SLAs
2. EVC Scheduling & Completion
3. Institutional Undertakings & Compliance Conditions
4. Lease Deeds & Prescribed Document Expiry/Renewal
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.models.entities import (
    Application,
    CalendarPolicy,
    Deadline,
    Document,
    EvcVisit,
    Notification,
    Undertaking,
    User,
)
from app.services.audit import write_audit
from app.services.calendar import add_working_days, get_default_policy
from app.services.notifications import notification_service


class DeadlineEngine:
    def sync_application_deadline(self, db: Session, app: Application) -> Deadline | None:
        """Sync application stage SLA deadline."""
        if not app.current_stage or app.status in {"decided", "closed"}:
            # Close existing active deadline if application is decided
            existing = (
                db.query(Deadline)
                .filter(
                    Deadline.deadline_type == "APPLICATION_SLA",
                    Deadline.linked_entity_type == "application",
                    Deadline.linked_entity_id == app.id,
                )
                .first()
            )
            if existing and existing.status not in {"completed", "cancelled"}:
                existing.status = "completed"
                existing.completed_at = clock.now()
                existing.last_updated_at = clock.now()
            return existing

        code = f"DDL-APP-{app.id}-{app.current_stage.stage_code}"
        deadline = (
            db.query(Deadline)
            .filter(
                Deadline.deadline_type == "APPLICATION_SLA",
                Deadline.linked_entity_type == "application",
                Deadline.linked_entity_id == app.id,
            )
            .first()
        )

        policy = get_default_policy(db)
        start_dt = app.stage_entered_at or app.submitted_at or clock.now()
        due_dt = app.sla_due_at or add_working_days(start_dt, app.current_stage.sla_days, policy, app.region_id)

        now = clock.now()
        aware_due = clock.aware(due_dt)
        status = "overdue" if aware_due and aware_due < now else "upcoming"

        if not deadline:
            deadline = Deadline(
                deadline_code=code,
                deadline_type="APPLICATION_SLA",
                linked_entity_type="application",
                linked_entity_id=app.id,
                institution_id=app.institution_id,
                application_id=app.id,
                responsible_user_id=app.assigned_officer_id,
                responsible_role="scrutiny_officer",
                title=f"Stage SLA: {app.current_stage.name} for {app.app_id}",
                start_date=start_dt,
                due_date=due_dt,
                calendar_policy_id=policy.id,
                status=status,
                created_at=now,
                last_updated_at=now,
            )
            db.add(deadline)
        else:
            deadline.title = f"Stage SLA: {app.current_stage.name} for {app.app_id}"
            deadline.start_date = start_dt
            deadline.due_date = due_dt
            deadline.responsible_user_id = app.assigned_officer_id
            if deadline.status != "paused":
                deadline.status = status
            deadline.last_updated_at = now

        return deadline

    def sync_evc_deadline(self, db: Session, evc: EvcVisit) -> Deadline | None:
        """Sync EVC scheduling or completion deadline."""
        app = db.get(Application, evc.application_id)
        if not app:
            return None

        is_completed = evc.status in {"Completed", "Report Uploaded"}
        status_val = "completed" if is_completed else ("overdue" if clock.aware(evc.scheduling_deadline) < clock.now() else "upcoming")

        code = f"DDL-EVC-{evc.id}"
        deadline = (
            db.query(Deadline)
            .filter(
                Deadline.deadline_type == "EVC_SCHEDULING",
                Deadline.linked_entity_type == "evc_visit",
                Deadline.linked_entity_id == evc.id,
            )
            .first()
        )

        now = clock.now()
        if not deadline:
            deadline = Deadline(
                deadline_code=code,
                deadline_type="EVC_SCHEDULING",
                linked_entity_type="evc_visit",
                linked_entity_id=evc.id,
                institution_id=app.institution_id,
                application_id=app.id,
                responsible_user_id=evc.chair_user_id,
                responsible_role="committee_member",
                title=f"EVC Scheduling Deadline for {app.app_id}",
                start_date=evc.eligible_since,
                due_date=evc.scheduling_deadline,
                status=status_val,
                completed_at=now if is_completed else None,
                created_at=now,
                last_updated_at=now,
            )
            db.add(deadline)
        else:
            deadline.due_date = evc.scheduling_deadline
            deadline.responsible_user_id = evc.chair_user_id
            if deadline.status != "paused":
                deadline.status = status_val
            if is_completed and not deadline.completed_at:
                deadline.completed_at = now
            deadline.last_updated_at = now

        return deadline

    def sync_undertaking_deadline(self, db: Session, ut: Undertaking) -> Deadline | None:
        """Sync undertaking fulfilment compliance deadline."""
        is_verified = ut.status == "Verified"
        status_val = "verified" if is_verified else ("overdue" if clock.aware(ut.due_date) < clock.now() else "upcoming")

        code = f"DDL-UT-{ut.id}"
        deadline = (
            db.query(Deadline)
            .filter(
                Deadline.deadline_type == "UNDERTAKING",
                Deadline.linked_entity_type == "undertaking",
                Deadline.linked_entity_id == ut.id,
            )
            .first()
        )

        now = clock.now()
        if not deadline:
            deadline = Deadline(
                deadline_code=code,
                deadline_type="UNDERTAKING",
                linked_entity_type="undertaking",
                linked_entity_id=ut.id,
                institution_id=ut.institution_id,
                application_id=ut.application_id,
                responsible_user_id=ut.verifying_officer_id,
                responsible_role="regional_officer",
                title=f"Compliance Undertaking: {ut.category}",
                start_date=now - timedelta(days=30),
                due_date=ut.due_date,
                status=status_val,
                verified_at=now if is_verified else None,
                created_at=now,
                last_updated_at=now,
            )
            db.add(deadline)
        else:
            deadline.due_date = ut.due_date
            deadline.responsible_user_id = ut.verifying_officer_id
            if deadline.status != "paused":
                deadline.status = status_val
            if is_verified and not deadline.verified_at:
                deadline.verified_at = now
            deadline.last_updated_at = now

        return deadline

    def sync_document_deadline(self, db: Session, doc: Document) -> Deadline | None:
        """Sync prescribed land lease deed or document expiry deadline."""
        is_verified = doc.status == "Verified"
        now = clock.now()
        aware_exp = clock.aware(doc.expiry_date)
        status_val = "overdue" if aware_exp and aware_exp < now else "upcoming"

        code = f"DDL-DOC-{doc.id}"
        deadline = (
            db.query(Deadline)
            .filter(
                Deadline.deadline_type == "DOCUMENT_EXPIRY",
                Deadline.linked_entity_type == "document",
                Deadline.linked_entity_id == doc.id,
            )
            .first()
        )

        if not deadline:
            deadline = Deadline(
                deadline_code=code,
                deadline_type="DOCUMENT_EXPIRY",
                linked_entity_type="document",
                linked_entity_id=doc.id,
                institution_id=doc.institution_id,
                title=f"Lease Validity Expiry: {doc.doc_type} ({doc.document_number})",
                start_date=doc.issue_date,
                due_date=doc.expiry_date,
                status=status_val,
                verified_at=now if is_verified else None,
                created_at=now,
                last_updated_at=now,
            )
            db.add(deadline)
        else:
            deadline.due_date = doc.expiry_date
            if deadline.status != "paused":
                deadline.status = status_val
            if is_verified and not deadline.verified_at:
                deadline.verified_at = now
            deadline.last_updated_at = now

        return deadline

    def sync_all(self, db: Session) -> int:
        """Initial / batch synchronization across all 4 modules."""
        count = 0
        for app in db.query(Application).all():
            self.sync_application_deadline(db, app)
            count += 1
        for evc in db.query(EvcVisit).all():
            self.sync_evc_deadline(db, evc)
            count += 1
        for ut in db.query(Undertaking).all():
            self.sync_undertaking_deadline(db, ut)
            count += 1
        for doc in db.query(Document).all():
            self.sync_document_deadline(db, doc)
            count += 1
        db.commit()
        return count

    def pause_deadline(self, db: Session, deadline_id: int, reason: str, actor: User) -> Deadline:
        dl = db.get(Deadline, deadline_id)
        if not dl:
            raise ValueError("Deadline not found")
        dl.status = "paused"
        dl.pause_reason = reason
        dl.last_updated_at = clock.now()
        write_audit(
            db,
            actor_id=actor.id,
            actor_role=actor.role.code,
            actor_label=actor.full_name,
            action="deadline.pause",
            entity_type="deadline",
            entity_id=dl.deadline_code,
            reason=reason,
        )
        db.commit()
        return dl

    def resume_deadline(self, db: Session, deadline_id: int, reason: str, actor: User) -> Deadline:
        dl = db.get(Deadline, deadline_id)
        if not dl:
            raise ValueError("Deadline not found")
        now = clock.now()
        dl.status = "overdue" if clock.aware(dl.due_date) < now else "upcoming"
        dl.pause_reason = None
        dl.last_updated_at = now
        write_audit(
            db,
            actor_id=actor.id,
            actor_role=actor.role.code,
            actor_label=actor.full_name,
            action="deadline.resume",
            entity_type="deadline",
            entity_id=dl.deadline_code,
            reason=reason,
        )
        db.commit()
        return dl


deadline_engine = DeadlineEngine()

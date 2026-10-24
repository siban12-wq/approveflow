from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    states: Mapped[list["State"]] = relationship(back_populates="region")


class State(Base):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    region: Mapped[Region] = relationship(back_populates="states")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), nullable=True)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    open_case_count: Mapped[int] = mapped_column(Integer, default=0)

    role: Mapped[Role] = relationship()
    region: Mapped[Region | None] = relationship()
    institution: Mapped["Institution | None"] = relationship(foreign_keys="User.institution_id")


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"))
    institution_type: Mapped[str] = mapped_column(String(64), default="Engineering")
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)
    compliance_score: Mapped[float] = mapped_column(Float, default=80.0)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)

    region: Mapped[Region] = relationship()
    state: Mapped[State] = relationship()


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    stages: Mapped[list["WorkflowStage"]] = relationship(
        back_populates="template", order_by="WorkflowStage.order_no", cascade="all, delete-orphan"
    )


class WorkflowStage(Base):
    __tablename__ = "workflow_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("workflow_templates.id"))
    order_no: Mapped[int] = mapped_column(Integer)
    stage_code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128))
    sla_days: Mapped[int] = mapped_column(Integer, default=15)
    allowed_roles: Mapped[list] = mapped_column(JSON, default=list)
    requires_remarks: Mapped[bool] = mapped_column(Boolean, default=False)
    human_only: Mapped[bool] = mapped_column(Boolean, default=True)

    template: Mapped[WorkflowTemplate] = relationship(back_populates="stages")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"))
    application_type: Mapped[str] = mapped_column(String(64))  # New / Extension / Closure
    template_id: Mapped[int] = mapped_column(ForeignKey("workflow_templates.id"))
    current_stage_id: Mapped[int | None] = mapped_column(ForeignKey("workflow_stages.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")  # open / returned / decided / closed
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)  # never auto-set
    decision_order_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stage_entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_status: Mapped[str] = mapped_column(String(32), default="on_track")
    assigned_officer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped[Institution] = relationship()
    template: Mapped[WorkflowTemplate] = relationship()
    current_stage: Mapped[WorkflowStage | None] = relationship()
    assigned_officer: Mapped[User | None] = relationship()
    region: Mapped[Region] = relationship()


class ApplicationStageHistory(Base):
    __tablename__ = "application_stage_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    from_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_in_stage_hours: Mapped[float | None] = mapped_column(Float, nullable=True)


class Deficiency(Base):
    __tablename__ = "deficiencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    raised_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    stage_id: Mapped[int] = mapped_column(ForeignKey("workflow_stages.id"))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="Open")  # Open / Responded / Closed
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvcVisit(Base):
    __tablename__ = "evc_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), unique=True)
    status: Mapped[str] = mapped_column(String(64), default="Pending Scheduling")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eligible_since: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduling_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    report_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)  # recommendation only
    chair_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class EvcMember(Base):
    __tablename__ = "evc_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("evc_visits.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class Undertaking(Base):
    __tablename__ = "undertakings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"))
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    condition_text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64))
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence_required: Mapped[str] = mapped_column(String(255), default="Supporting PDF")
    status: Mapped[str] = mapped_column(String(32), default="Open")
    verifying_officer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class UndertakingSubmission(Base):
    __tablename__ = "undertaking_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    undertaking_id: Mapped[int] = mapped_column(ForeignKey("undertakings.id"))
    file_path: Mapped[str] = mapped_column(String(512))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    receipt: Mapped[str] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"))
    doc_type: Mapped[str] = mapped_column(String(64))  # lease_deed etc
    document_number: Mapped[str] = mapped_column(String(64))
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="Valid")
    current_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    version_no: Mapped[int] = mapped_column(Integer)
    file_path: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    trigger_type: Mapped[str] = mapped_column(String(32))
    offset_days: Mapped[int] = mapped_column(Integer, default=0)
    channels: Mapped[dict] = mapped_column(JSON, default=dict)
    recipient_roles: Mapped[list] = mapped_column(JSON, default=list)
    severity: Mapped[str] = mapped_column(String(16), default="INFO")
    template_id: Mapped[int | None] = mapped_column(ForeignKey("notification_templates.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EscalationRule(Base):
    __tablename__ = "escalation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    level: Mapped[int] = mapped_column(Integer)
    threshold_days_overdue: Mapped[int] = mapped_column(Integer)
    escalate_to_role: Mapped[str] = mapped_column(String(64))
    region_scoped: Mapped[bool] = mapped_column(Boolean, default=True)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("dedupe_key", name="uq_notification_dedupe"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("alert_rules.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0)
    severity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    channel: Mapped[str] = mapped_column(String(16), default="in_app")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snooze_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), index=True)


class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    level: Mapped[int] = mapped_column(Integer)
    escalated_to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_role: Mapped[str] = mapped_column(String(64))
    actor_label: Mapped[str] = mapped_column(String(128), default="")
    action: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    row_hash: Mapped[str] = mapped_column(String(64))


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    items_checked: Mapped[int] = mapped_column(Integer, default=0)
    alerts_created: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)

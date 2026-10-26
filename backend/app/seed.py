"""Simulated demo data. Every record is fictional."""

from __future__ import annotations

import random
from datetime import timedelta

from sqlalchemy import select

from app.core.clock import clock
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models.entities import (
    AlertRule,
    Application,
    Base,
    CalendarHoliday,
    CalendarPolicy,
    Deadline,
    Document,
    DocumentExtraction,
    Escalation,
    EscalationRule,
    EvcVisit,
    Institution,
    NotificationTemplate,
    Region,
    Role,
    State,
    Undertaking,
    User,
    WorkflowStage,
    WorkflowTemplate,
)
from app.services.deadline_engine import deadline_engine
from app.workflows.engine import TYPE_TO_TEMPLATE, engine as wf

DEMO_PASSWORD = "Demo@123"

REGIONS = [
    ("ER", "Eastern"),
    ("WR", "Western"),
    ("NR", "Northern"),
    ("SR", "Southern"),
    ("CR", "Central"),
    ("NWR", "North-Western"),
    ("SWR", "South-Western"),
]

STATES = {
    "ER": ["West Bengal", "Odisha", "Bihar"],
    "WR": ["Maharashtra", "Goa", "Gujarat"],
    "NR": ["Uttar Pradesh", "Uttarakhand", "Delhi"],
    "SR": ["Tamil Nadu", "Kerala", "Puducherry"],
    "CR": ["Madhya Pradesh", "Chhattisgarh"],
    "NWR": ["Rajasthan", "Haryana", "Punjab"],
    "SWR": ["Karnataka", "Andhra Pradesh", "Telangana"],
}

COLLEGE_STEMS = [
    "Nalanda", "Vikramshila", "Kaveri", "Godavari", "Yamuna", "Sabarmati", "Tungabhadra",
    "Aravalli", "Nilgiri", "Satpura", "Vindhya", "Chilika", "Sundarban", "Konkan", "Malabar",
    "Deccan", "Charminar", "Mysuru", "Indraprastha", "Ujjain", "Pataliputra", "Kanchi",
    "Hampi", "Ajanta", "Ellora", "Shivalik", "Meghna", "Mahanadi", "Krishna", "Ganga",
]

TEMPLATES = [
    ("ONLY_SCRUTINY", "Only Scrutiny", ["SUBMITTED", "SCRUTINY", "DECISION_PENDING", "CLOSED"]),
    ("SCRUTINY_EVC", "Scrutiny + EVC", ["SUBMITTED", "SCRUTINY", "EVC_QUEUE", "EVC_VISIT", "EVC_REPORT_REVIEW", "DECISION_PENDING", "CLOSED"]),
    ("EVC_SAC_SHC", "EVC + SAC/SHC", ["SUBMITTED", "EVC_QUEUE", "EVC_VISIT", "EVC_REPORT_REVIEW", "SAC_SHC", "DECISION_PENDING", "CLOSED"]),
    ("ONLY_EVC", "Only EVC", ["SUBMITTED", "EVC_QUEUE", "EVC_VISIT", "EVC_REPORT_REVIEW", "DECISION_PENDING", "CLOSED"]),
    ("SCRUTINY_EVC_SAC_SHC", "Scrutiny + EVC + SAC/SHC", ["SUBMITTED", "SCRUTINY", "EVC_QUEUE", "EVC_VISIT", "EVC_REPORT_REVIEW", "SAC_SHC", "DECISION_PENDING", "CLOSED"]),
]

STAGE_META = {
    "SUBMITTED": ("Submitted", 5, ["institution_user"], False),
    "SCRUTINY": ("Scrutiny", 15, ["regional_officer", "scrutiny_officer"], True),
    "EVC_QUEUE": ("EVC Queue", 30, ["regional_officer", "evc_coordinator"], False),
    "EVC_VISIT": ("EVC Visit", 15, ["committee_member", "regional_officer", "evc_coordinator"], True),
    "EVC_REPORT_REVIEW": ("EVC Report Review", 10, ["regional_officer", "bureau_officer", "evc_coordinator"], True),
    "SAC_SHC": ("SAC/SHC", 20, ["committee_member", "bureau_officer", "competent_authority"], True),
    "DECISION_PENDING": ("Decision Pending", 15, ["bureau_officer", "super_admin", "competent_authority"], True),
    "CLOSED": ("Closed", 0, ["super_admin"], False),
}

TYPES = ["New", "Extension", "Closure", "Increase in Intake", "New Campus"]


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.execute(select(Role)).first():
            return
        seed_all(db)
    finally:
        db.close()


def seed_all(db) -> None:
    now = clock.now()
    roles = {}
    for code, name in [
        ("super_admin", "System Administrator"),
        ("bureau_officer", "Bureau Officer"),
        ("regional_officer", "Regional Officer"),
        ("scrutiny_officer", "Scrutiny Officer"),
        ("committee_member", "EVC Committee Member"),
        ("evc_coordinator", "EVC Coordinator"),
        ("competent_authority", "Competent Authority"),
        ("institution_user", "Institution Administrator"),
    ]:
        r = Role(code=code, name=name)
        db.add(r)
        db.flush()
        roles[code] = r

    regions: list[Region] = []
    states_by_region: dict[int, list[State]] = {}
    for code, name in REGIONS:
        rg = Region(code=code, name=name)
        db.add(rg)
        db.flush()
        regions.append(rg)
        states_by_region[rg.id] = []
        for sn in STATES[code]:
            st = State(name=sn, region_id=rg.id)
            db.add(st)
            db.flush()
            states_by_region[rg.id].append(st)

    hashed = hash_password(DEMO_PASSWORD)

    def _acct(**kwargs):
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("account_status", "active")
        kwargs.setdefault("email_verified", True)
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("token_version", 0)
        return User(**kwargs)

    super_u = _acct(email="super@approveflow.demo", full_name="Ananya Rao", hashed_password=hashed, role_id=roles["super_admin"].id)
    bureau = _acct(email="bureau@approveflow.demo", full_name="Vikram Menon", hashed_password=hashed, role_id=roles["bureau_officer"].id)
    scrutiny = _acct(email="scrutiny@approveflow.demo", full_name="Kavita Sharma", hashed_password=hashed, role_id=roles["scrutiny_officer"].id)
    authority = _acct(email="authority@approveflow.demo", full_name="Justice (Retd.) N. Krishnan", hashed_password=hashed, role_id=roles["competent_authority"].id)
    db.add_all([super_u, bureau, scrutiny, authority])
    db.flush()

    regional_users: list[User] = []
    for i, rg in enumerate(regions):
        u = _acct(
            email=f"ro.{rg.code.lower()}@approveflow.demo" if i else "regional@approveflow.demo",
            full_name=f"RO {rg.name}",
            hashed_password=hashed,
            role_id=roles["regional_officer"].id,
            region_id=rg.id,
        )
        db.add(u)
        db.flush()
        regional_users.append(u)

    committee = _acct(
        email="committee@approveflow.demo",
        full_name="Dr. Meera Iyer",
        hashed_password=hashed,
        role_id=roles["committee_member"].id,
    )
    evc_coord = _acct(
        email="evc@approveflow.demo",
        full_name="Arjun Deshmukh",
        hashed_password=hashed,
        role_id=roles["evc_coordinator"].id,
    )
    db.add_all([committee, evc_coord])
    db.flush()

    institutions: list[Institution] = []
    for i in range(60):
        rg = regions[i % len(regions)]
        st_list = states_by_region[rg.id]
        st = st_list[i % len(st_list)]
        stem = COLLEGE_STEMS[i % len(COLLEGE_STEMS)]
        inst = Institution(
            code=f"INS-{1000 + i}",
            name=f"{stem} Institute of Technology",
            region_id=rg.id,
            state_id=st.id,
            is_new=i % 11 == 0,
            compliance_score=round(55 + (i % 40) + random.random() * 5, 1),
            simulated=True,
        )
        db.add(inst)
        db.flush()
        institutions.append(inst)

    inst_user = _acct(
        email="institution@approveflow.demo",
        full_name="Principal, Nalanda Institute of Technology",
        hashed_password=hashed,
        role_id=roles["institution_user"].id,
        institution_id=institutions[0].id,
        region_id=institutions[0].region_id,
    )
    pending = _acct(
        email="pending@approveflow.demo",
        full_name="Dr. S. Banerjee",
        hashed_password=hashed,
        role_id=roles["institution_user"].id,
        is_active=False,
        account_status="pending",
        email_verified=True,
        requested_role="institution_user",
        requested_institution_name="Chilika College of Engineering (demo request)",
        status_reason="Awaiting institutional verification",
    )
    db.add_all([inst_user, pending])
    db.flush()

    tpls: dict[str, WorkflowTemplate] = {}
    for code, name, stages in TEMPLATES:
        tpl = WorkflowTemplate(code=code, name=name, description=f"Simulated path: {name}", is_active=True, version=1)
        db.add(tpl)
        db.flush()
        for idx, sc in enumerate(stages, start=1):
            meta = STAGE_META[sc]
            db.add(
                WorkflowStage(
                    template_id=tpl.id,
                    order_no=idx,
                    stage_code=sc,
                    name=meta[0],
                    sla_days=meta[1],
                    allowed_roles=meta[2],
                    requires_remarks=meta[3],
                    human_only=True,
                )
            )
        db.flush()
        tpls[code] = tpl

    # Notification templates + rules
    t_sla = NotificationTemplate(
        code="SLA_ALERT",
        subject="SLA {severity} for {app_id}",
        body="{institution} application {app_id} is at {stage}. Due {due_date}. Days left: {days_left}. Officer: {officer}. Automated alerts support, but do not replace, decisions of the competent authority.",
    )
    t_evc = NotificationTemplate(code="EVC_ALERT", subject="EVC reminder {app_id}", body="EVC for {institution} ({app_id}) due {due_date}. Days left {days_left}.")
    t_ut = NotificationTemplate(code="UT_ALERT", subject="Undertaking due {app_id}", body="Undertaking for {institution} due {due_date}. Days left {days_left}.")
    t_doc = NotificationTemplate(code="DOC_ALERT", subject="Document {app_id} expiry", body="Document {app_id} expires {due_date}. Days left {days_left}.")
    db.add_all([t_sla, t_evc, t_ut, t_doc])
    db.flush()

    def rule(code, et, trig, offset, sev, tpl, roles, extra=0):
        db.add(
            AlertRule(
                code=code,
                entity_type=et,
                trigger_type=trig,
                offset_days=offset,
                channels={"in_app": True, "email": False},
                recipient_roles=roles,
                severity=sev,
                template_id=tpl,
                is_active=True,
            )
        )

    rule("APP_SLA_80", "APPLICATION", "AGEING", 0, "WARNING", t_sla.id, ["regional_officer", "bureau_officer"])
    rule("APP_SLA_BREACH", "APPLICATION", "AGEING", 0, "CRITICAL", t_sla.id, ["regional_officer", "bureau_officer"])
    rule("APP_SLA_EVERY_3", "APPLICATION", "AFTER_DUE", 3, "CRITICAL", t_sla.id, ["regional_officer"])
    for off, sev in [(-7, "INFO"), (-3, "WARNING"), (-1, "WARNING"), (0, "CRITICAL")]:
        trig = "ON_DUE" if off == 0 else "BEFORE_DUE"
        rule(f"EVC_T{off}", "EVC", trig, off, sev, t_evc.id, ["regional_officer", "committee_member"])
    rule("EVC_OVERDUE_DAILY", "EVC", "AFTER_DUE", 1, "CRITICAL", t_evc.id, ["regional_officer", "bureau_officer"])
    for off in (-30, -15, -7, -1, 0):
        trig = "ON_DUE" if off == 0 else "BEFORE_DUE"
        rule(f"UT_T{off}", "UNDERTAKING", trig, off, "WARNING" if off < 0 else "CRITICAL", t_ut.id, ["institution_user", "regional_officer"])
    rule("UT_OVERDUE_DAILY", "UNDERTAKING", "AFTER_DUE", 1, "CRITICAL", t_ut.id, ["institution_user", "regional_officer"])
    for off in (-90, -60, -30, -7, 0):
        trig = "ON_DUE" if off == 0 else "BEFORE_DUE"
        sev = "CRITICAL" if off >= -7 else "WARNING"
        rule(f"DOC_T{off}", "DOCUMENT", trig, off, sev, t_doc.id, ["institution_user", "regional_officer"])
    rule("DOC_OVERDUE_WEEKLY", "DOCUMENT", "AFTER_DUE", 7, "CRITICAL", t_doc.id, ["regional_officer", "bureau_officer"])

    for et in ("APPLICATION", "EVC", "UNDERTAKING", "DOCUMENT"):
        db.add(EscalationRule(entity_type=et, level=1, threshold_days_overdue=3, escalate_to_role="regional_officer", region_scoped=True))
        db.add(EscalationRule(entity_type=et, level=2, threshold_days_overdue=10, escalate_to_role="bureau_officer", region_scoped=False))
        db.add(EscalationRule(entity_type=et, level=3, threshold_days_overdue=20, escalate_to_role="super_admin", region_scoped=False))

    db.flush()

    # Reload templates with stages
    tpls = {
        t.code: t
        for t in db.execute(select(WorkflowTemplate).execution_options()).scalars().all()
    }
    from sqlalchemy.orm import joinedload

    tpls = {
        t.code: t
        for t in db.query(WorkflowTemplate).options(joinedload(WorkflowTemplate.stages)).all()
    }

    rng = random.Random(42)
    apps: list[Application] = []
    for i in range(150):
        inst = institutions[i % 60]
        atype = TYPES[i % len(TYPES)]
        code = TYPE_TO_TEMPLATE[atype]
        tpl = tpls[code]
        stages = sorted(tpl.stages, key=lambda s: s.order_no)
        # Spread across stages, leave Closed as last option
        open_stages = [s for s in stages if s.stage_code != "CLOSED"]
        if i < 8:
            stage = next(s for s in stages if s.stage_code == "SCRUTINY") if any(s.stage_code == "SCRUTINY" for s in stages) else open_stages[1]
        elif i < 16:
            stage = next((s for s in stages if s.stage_code == "EVC_QUEUE"), open_stages[-2])
        elif i < 24:
            stage = next((s for s in stages if s.stage_code == "DECISION_PENDING"), open_stages[-1])
        else:
            stage = open_stages[i % len(open_stages)]
        submitted = now - timedelta(days=rng.randint(2, 80))
        # Deliberate SLA scenarios
        if i % 17 == 0:
            entered = now - timedelta(days=stage.sla_days + 12)
            sla_status = "overdue"
        elif i % 11 == 0:
            entered = now - timedelta(days=max(stage.sla_days - 2, 1))
            sla_status = "approaching"
        else:
            entered = now - timedelta(days=rng.randint(1, max(stage.sla_days - 3, 1)))
            sla_status = "on_track"
        officer = regional_users[inst.region_id % len(regional_users)]
        app = Application(
            app_id=f"APP-2026-{i + 1:04d}",
            institution_id=inst.id,
            application_type=atype,
            template_id=tpl.id,
            current_stage_id=stage.id,
            status="open",
            stage_entered_at=entered,
            sla_due_at=entered + timedelta(days=stage.sla_days),
            sla_status=sla_status,
            assigned_officer_id=officer.id,
            region_id=inst.region_id,
            submitted_at=submitted,
            last_updated_at=entered,
            simulated=True,
        )
        app.current_stage = stage
        db.add(app)
        db.flush()
        apps.append(app)
        wf._history(db, app, None, stage.stage_code, "start", officer, "Simulated intake", None)

    # Returned + resubmitted scenario on first app
    from app.models.entities import Deficiency, ApplicationStageHistory

    apps[0].status = "returned"
    db.add(
        Deficiency(
            application_id=apps[0].id,
            raised_by=regional_users[0].id,
            stage_id=apps[0].current_stage_id,
            description="Land records annexure is incomplete; please upload the certified copy.",
            status="Open",
            response_due_at=now + timedelta(days=10),
        )
    )

    # EVC visits with T-1, T-3, T-7
    evc_apps = [a for a in apps if a.current_stage and a.current_stage.stage_code in {"EVC_QUEUE", "EVC_VISIT"}][:12]
    offsets = [1, 3, 7, 0, -2, 14]
    for idx, a in enumerate(evc_apps):
        off = offsets[idx % len(offsets)]
        db.add(
            EvcVisit(
                application_id=a.id,
                status="Pending Scheduling" if off != 0 else "Scheduled",
                scheduled_at=now + timedelta(days=off) if off == 0 else None,
                eligible_since=now - timedelta(days=20),
                scheduling_deadline=now + timedelta(days=off if off >= 0 else -2),
                venue="Institution campus" if off == 0 else None,
            )
        )

    # Undertakings
    for i, inst in enumerate(institutions[:18]):
        due_offsets = [7, 15, 30, -4, 1, 45]
        due = now + timedelta(days=due_offsets[i % len(due_offsets)])
        status = "Overdue" if due_offsets[i % len(due_offsets)] < 0 else "Open"
        db.add(
            Undertaking(
                institution_id=inst.id,
                application_id=apps[i].id,
                condition_text="Submit occupancy certificate for the newly added workshop block.",
                category="Infrastructure",
                due_date=due,
                status=status,
            )
        )

    # Documents / leases: 7, 30, 90, expired
    for i, inst in enumerate(institutions[:12]):
        lefts = [7, 30, 90, -12, 60, 120]
        left = lefts[i % len(lefts)]
        status = "Expired" if left < 0 else ("Expiring Soon" if left <= 90 else "Valid")
        db.add(
            Document(
                institution_id=inst.id,
                doc_type="lease_deed",
                document_number=f"LEASE-{inst.code}",
                issue_date=now - timedelta(days=365 * 5),
                expiry_date=now + timedelta(days=left),
                status=status,
                current_hash="demo" + "a" * 28,
            )
        )

    # Seed a couple of escalations so the timeline is visible
    overdue_apps = [a for a in apps if a.sla_status == "overdue"][:6]
    for i, a in enumerate(overdue_apps):
        level = (i % 3) + 1
        db.add(
            Escalation(
                entity_type="APPLICATION",
                entity_id=a.id,
                level=level,
                escalated_to_user_id=bureau.id if level >= 2 else regional_users[0].id,
                triggered_at=now - timedelta(days=level * 2),
                region_id=a.region_id,
            )
        )

    db.commit()


AUTH_ROLES = [
    ("super_admin", "System Administrator"),
    ("bureau_officer", "Bureau Officer"),
    ("regional_officer", "Regional Officer"),
    ("scrutiny_officer", "Scrutiny Officer"),
    ("committee_member", "EVC Committee Member"),
    ("evc_coordinator", "EVC Coordinator"),
    ("competent_authority", "Competent Authority"),
    ("institution_user", "Institution Administrator"),
]


def ensure_auth_accounts() -> None:
    """Add new roles/demo users to an already-seeded database without wiping data."""
    db = SessionLocal()
    try:
        if not db.execute(select(Role)).first():
            return
        existing = {r.code for r in db.query(Role).all()}
        for code, name in AUTH_ROLES:
            if code not in existing:
                db.add(Role(code=code, name=name))
        db.flush()
        roles = {r.code: r for r in db.query(Role).all()}
        hashed = hash_password(DEMO_PASSWORD)
        extras = [
            ("scrutiny@approveflow.demo", "Kavita Sharma", "scrutiny_officer"),
            ("evc@approveflow.demo", "Arjun Deshmukh", "evc_coordinator"),
            ("authority@approveflow.demo", "Justice (Retd.) N. Krishnan", "competent_authority"),
        ]
        for email, name, role in extras:
            if role not in roles:
                continue
            if db.query(User).filter(User.email == email).first():
                continue
            db.add(
                User(
                    email=email,
                    full_name=name,
                    hashed_password=hashed,
                    role_id=roles[role].id,
                    is_active=True,
                    account_status="active",
                    email_verified=True,
                    created_at=clock.now(),
                    token_version=0,
                )
            )
        for user in db.query(User).all():
            if not user.account_status:
                user.account_status = "active" if user.is_active else "pending"
            if user.token_version is None:
                user.token_version = 0

        # Ensure default Calendar Policy
        cal = db.query(CalendarPolicy).filter(CalendarPolicy.code == "AICTE_STD_5DAY").first()
        if not cal:
            cal = CalendarPolicy(
                code="AICTE_STD_5DAY",
                name="AICTE National 5-Day Administrative Calendar",
                working_weekdays=[0, 1, 2, 3, 4],
                is_default=True,
                description="Official administrative 5-day week (Mon-Fri) excluding gazetted central holidays",
            )
            db.add(cal)
            db.flush()

            holidays = [
                ("Republic Day", "2026-01-26"),
                ("Maha Shivratri", "2026-02-15"),
                ("Holi", "2026-03-04"),
                ("Eid-ul-Fitr", "2026-03-21"),
                ("Good Friday", "2026-04-03"),
                ("Mahavir Jayanti", "2026-03-31"),
                ("Buddha Purnima", "2026-05-01"),
                ("Independence Day", "2026-08-15"),
                ("Milad-un-Nabi", "2026-08-26"),
                ("Mahatma Gandhi Birthday", "2026-10-02"),
                ("Dussehra", "2026-10-20"),
                ("Diwali (Deepavali)", "2026-11-08"),
                ("Guru Nanak Birthday", "2026-11-24"),
                ("Christmas Day", "2026-12-25"),
            ]
            for h_name, h_date in holidays:
                db.add(CalendarHoliday(policy_id=cal.id, name=h_name, holiday_date=h_date))

        # Ensure sample OCR extractions for documents
        if not db.query(DocumentExtraction).first():
            docs = db.query(Document).limit(5).all()
            for doc in docs:
                db.add(
                    DocumentExtraction(
                        document_id=doc.id,
                        file_path=f"demo/lease_{doc.id}.pdf",
                        extracted_type="Registered Land Lease Deed",
                        extracted_institution=doc.institution.name if doc.institution else "Demo Institute of Technology",
                        extracted_premises_address="Plot No. 12-A, Knowledge Park II, Greater Noida, Gautam Buddha Nagar, Uttar Pradesh - 201310",
                        candidate_commencement_date=doc.issue_date.date().isoformat() if doc.issue_date else "2020-04-01",
                        candidate_expiry_date=doc.expiry_date.date().isoformat() if doc.expiry_date else "2050-03-31",
                        renewal_clause_found=True,
                        confidence_score=0.92,
                        extracted_snippet=f"THIS LEASE DEED entered between Greater Noida Industrial Development Authority (Lessor) and {doc.institution.name if doc.institution else 'Lessee'} for a period of 30 years commencing from {doc.issue_date.date().isoformat() if doc.issue_date else '2020-04-01'} and valid through {doc.expiry_date.date().isoformat() if doc.expiry_date else '2050-03-31'}.",
                        source_page_no=2,
                        extraction_status="pending_human_review",
                        created_at=clock.now(),
                    )
                )

        # Synchronize Unified Deadline Engine across all applications, evc, undertakings, and documents
        if db.query(Deadline).count() == 0:
            deadline_engine.sync_all(db)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.execute(select(Role)).first():
            print("Database already seeded.")
        else:
            seed_all(db)
            print("Seeded simulated demo data.")
    finally:
        db.close()

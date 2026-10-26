from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pytest

from app.core.clock import clock
from app.db.session import get_db
from app.main import app
from app.models.entities import (
    Application,
    CalendarHoliday,
    CalendarPolicy,
    Deadline,
    Document,
    Institution,
    WorkflowTemplate,
)
from app.services.calendar import add_working_days, is_working_day
from app.services.deadline_engine import deadline_engine


def _client(db) -> TestClient:
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def _seed_test_records(db):
    inst = db.query(Institution).first()
    tpl = db.query(WorkflowTemplate).first()
    stage = tpl.stages[0] if tpl and tpl.stages else None
    now = clock.now()
    app = Application(
        app_id="APP-TEST-001",
        institution_id=inst.id,
        application_type="New",
        template_id=tpl.id,
        current_stage_id=stage.id if stage else None,
        status="open",
        region_id=inst.region_id,
        submitted_at=now,
        last_updated_at=now,
    )
    db.add(app)
    doc = Document(
        institution_id=inst.id,
        doc_type="lease_deed",
        document_number="LD-TEST-123",
        issue_date=now,
        expiry_date=now + timedelta(days=365),
        status="Valid",
    )
    db.add(doc)
    db.commit()


def test_working_day_calculations_and_holidays(db):
    policy = CalendarPolicy(
        code="TEST_5DAY",
        name="Test 5-Day Calendar",
        working_weekdays=[0, 1, 2, 3, 4],  # Mon-Fri
        is_default=False,
    )
    db.add(policy)
    db.flush()

    # Friday 2026-10-23
    friday = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)
    assert is_working_day(friday, policy) is True

    # Saturday 2026-10-24
    saturday = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)
    assert is_working_day(saturday, policy) is False

    # Add a public holiday on Monday 2026-10-26
    h = CalendarHoliday(policy_id=policy.id, name="Test Holiday", holiday_date="2026-10-26")
    db.add(h)
    db.commit()

    # Monday should now not be a working day
    monday = datetime(2026, 10, 26, 10, 0, tzinfo=timezone.utc)
    assert is_working_day(monday, policy) is False

    # Tuesday 2026-10-27 is a working day
    tuesday = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
    assert is_working_day(tuesday, policy) is True

    # Adding 1 working day from Friday 2026-10-23:
    # Sat (no), Sun (no), Mon (holiday - no), Tue (working day 1)
    due = add_working_days(friday, 1, policy)
    assert due.date().isoformat() == "2026-10-27"


def test_unified_deadline_engine_pause_and_resume(db):
    _seed_test_records(db)
    deadline_engine.sync_all(db)
    dl = db.query(Deadline).first()
    assert dl is not None

    client = _client(db)
    admin_login = client.post("/api/v1/auth/login", json={"email": "super@test.demo", "password": "Demo@123"}).json()
    token = admin_login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Pause deadline
    pause_res = client.post(
        f"/api/v1/deadlines/{dl.id}/pause",
        json={"reason": "Court stay order received on land survey"},
        headers=headers,
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "paused"

    db.refresh(dl)
    assert dl.status == "paused"
    assert dl.pause_reason == "Court stay order received on land survey"

    # Resume deadline
    resume_res = client.post(
        f"/api/v1/deadlines/{dl.id}/resume",
        json={"reason": "Stay order vacated by High Court"},
        headers=headers,
    )
    assert resume_res.status_code == 200
    db.refresh(dl)
    assert dl.status in {"upcoming", "overdue", "pending"}
    assert dl.pause_reason is None


def test_deadlines_api_list_and_summary(db):
    _seed_test_records(db)
    deadline_engine.sync_all(db)
    client = _client(db)
    admin_login = client.post("/api/v1/auth/login", json={"email": "super@test.demo", "password": "Demo@123"}).json()
    headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    res = client.get("/api/v1/deadlines?page_size=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] > 0

    sum_res = client.get("/api/v1/deadlines/summary", headers=headers)
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert "by_type" in summary
    assert "APPLICATION_SLA" in summary["by_type"]
    assert "DOCUMENT_EXPIRY" in summary["by_type"]

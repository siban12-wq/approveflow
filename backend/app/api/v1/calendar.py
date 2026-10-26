"""API endpoints for working-day calendar policies and date calculation.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.entities import CalendarHoliday, CalendarPolicy, User
from app.services.calendar import (
    add_working_days,
    count_working_days,
    get_default_policy,
    is_working_day,
)

router = APIRouter()


class CalculateRequest(BaseModel):
    start_date: datetime | None = None
    working_days: int = 15
    policy_id: int | None = None
    region_id: int | None = None


@router.get("/policies")
def list_policies(db: Session = Depends(get_db)) -> list[dict]:
    policies = db.query(CalendarPolicy).options(joinedload(CalendarPolicy.holidays)).all()
    if not policies:
        get_default_policy(db)
        db.commit()
        policies = db.query(CalendarPolicy).options(joinedload(CalendarPolicy.holidays)).all()

    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "working_weekdays": p.working_weekdays,
            "is_default": p.is_default,
            "description": p.description,
            "holiday_count": len(p.holidays),
        }
        for p in policies
    ]


@router.get("/holidays")
def list_holidays(
    policy_id: int | None = None,
    region_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    query = db.query(CalendarHoliday)
    if policy_id:
        query = query.filter(CalendarHoliday.policy_id == policy_id)
    if region_id:
        query = query.filter(CalendarHoliday.region_id == region_id)

    rows = query.order_by(CalendarHoliday.holiday_date.asc()).all()
    return [
        {
            "id": h.id,
            "policy_id": h.policy_id,
            "name": h.name,
            "holiday_date": h.holiday_date,
            "region_id": h.region_id,
        }
        for h in rows
    ]


@router.post("/calculate")
def calculate_timeline(
    body: CalculateRequest,
    db: Session = Depends(get_db),
) -> dict:
    policy = None
    if body.policy_id:
        policy = db.get(CalendarPolicy, body.policy_id)
    if not policy:
        policy = get_default_policy(db)

    start = body.start_date or clock.now()
    due_dt = add_working_days(start, body.working_days, policy, body.region_id)
    elapsed = count_working_days(start, due_dt, policy, body.region_id)

    return {
        "start_date": start.isoformat(),
        "working_days_requested": body.working_days,
        "calculated_due_date": due_dt.isoformat(),
        "verified_working_days": elapsed,
        "is_start_working_day": is_working_day(start, policy, body.region_id),
        "is_due_working_day": is_working_day(due_dt, policy, body.region_id),
        "policy_used": policy.name,
    }

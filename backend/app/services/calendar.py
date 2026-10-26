"""Working-day calendar calculation engine.
Handles weekend exclusions, gazetted public holidays, region-specific holidays,
and statutory administrative SLA calculation rules.
"""

from __future__ import annotations
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.models.entities import CalendarHoliday, CalendarPolicy

DEFAULT_WORKING_WEEKDAYS = [0, 1, 2, 3, 4]  # Monday to Friday


def get_default_policy(db: Session) -> CalendarPolicy:
    policy = db.query(CalendarPolicy).filter(CalendarPolicy.is_default.is_(True)).first()
    if not policy:
        policy = CalendarPolicy(
            code="AICTE_STD_5DAY",
            name="AICTE National 5-Day Administrative Calendar",
            working_weekdays=DEFAULT_WORKING_WEEKDAYS,
            is_default=True,
            description="Official administrative 5-day week (Mon-Fri) excluding gazetted central holidays",
        )
        db.add(policy)
        db.flush()
    return policy


def _extract_holiday_dates(policy: CalendarPolicy | None, region_id: int | None = None) -> set[str]:
    if not policy:
        return set()
    from sqlalchemy.orm import object_session
    s = object_session(policy)
    if s is not None and getattr(policy, "id", None):
        q = s.query(CalendarHoliday).filter(CalendarHoliday.policy_id == policy.id)
        if region_id is not None:
            q = q.filter((CalendarHoliday.region_id.is_(None)) | (CalendarHoliday.region_id == region_id))
        return {h.holiday_date for h in q.all()}

    holidays = set()
    if getattr(policy, "holidays", None):
        for h in policy.holidays:
            if h.region_id is None or h.region_id == region_id:
                holidays.add(h.holiday_date)
    return holidays


def is_working_day(
    d: date | datetime,
    policy: CalendarPolicy | None = None,
    region_id: int | None = None,
) -> bool:
    """Check if a date is a working day under the given calendar policy."""
    check_date = d.date() if isinstance(d, datetime) else d
    weekdays = policy.working_weekdays if (policy and policy.working_weekdays) else DEFAULT_WORKING_WEEKDAYS
    if check_date.weekday() not in weekdays:
        return False
    holidays = _extract_holiday_dates(policy, region_id)
    iso_date = check_date.isoformat()
    return iso_date not in holidays


def get_next_working_day(
    d: date | datetime,
    policy: CalendarPolicy | None = None,
    region_id: int | None = None,
) -> date:
    """Find the next working day on or after the specified date."""
    current = d.date() if isinstance(d, datetime) else d
    while not is_working_day(current, policy, region_id):
        current += timedelta(days=1)
    return current


def add_working_days(
    start_dt: datetime,
    working_days: int,
    policy: CalendarPolicy | None = None,
    region_id: int | None = None,
) -> datetime:
    """Add N working days to start_dt.
    Administrative standard convention: If submitted on day T, counting begins on T+1.
    Preserves time of day and returns UTC-aware datetime.
    """
    if working_days <= 0:
        return clock.aware(start_dt) or datetime.now(timezone.utc)

    current_date = (clock.aware(start_dt) or datetime.now(timezone.utc)).date()
    # Advance to the first counting day
    current_date += timedelta(days=1)
    days_counted = 0

    while days_counted < working_days:
        if is_working_day(current_date, policy, region_id):
            days_counted += 1
            if days_counted == working_days:
                break
        current_date += timedelta(days=1)

    due_time = start_dt.timetz() if isinstance(start_dt, datetime) else time(17, 30, tzinfo=timezone.utc)
    return datetime.combine(current_date, due_time)


def count_working_days(
    start_dt: datetime,
    end_dt: datetime,
    policy: CalendarPolicy | None = None,
    region_id: int | None = None,
) -> int:
    """Count elapsed working days between start_dt and end_dt."""
    s = (clock.aware(start_dt) or datetime.now(timezone.utc)).date()
    e = (clock.aware(end_dt) or datetime.now(timezone.utc)).date()
    if s >= e:
        return 0

    count = 0
    curr = s + timedelta(days=1)
    while curr <= e:
        if is_working_day(curr, policy, region_id):
            count += 1
        curr += timedelta(days=1)
    return count


def calculate_due_date(
    start_dt: datetime,
    duration_days: int,
    policy: CalendarPolicy | None = None,
    region_id: int | None = None,
) -> datetime:
    """Compute SLA due datetime respecting working-day policies."""
    return add_working_days(start_dt, duration_days, policy, region_id)

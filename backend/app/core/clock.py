"""Injectable clock so jobs and the demo can time-travel without mutating real UTC."""

from datetime import datetime, timedelta, timezone


class Clock:
    def __init__(self) -> None:
        self._offset = timedelta(0)

    def now(self) -> datetime:
        return datetime.now(timezone.utc) + self._offset

    def aware(self, dt: datetime | None) -> datetime | None:
        """SQLite drops tzinfo on round-trip; always compare UTC-aware values."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def days_since(self, dt: datetime | None) -> int:
        if dt is None:
            return 0
        aware = self.aware(dt)
        if aware is None:
            return 0
        return (self.now() - aware).days

    def set_offset_days(self, days: int) -> None:
        self._offset = timedelta(days=days)

    def advance_days(self, days: int) -> datetime:
        self._offset += timedelta(days=days)
        return self.now()

    def reset(self) -> None:
        self._offset = timedelta(0)


clock = Clock()

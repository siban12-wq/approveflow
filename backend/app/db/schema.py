"""Lightweight additive schema updates for existing SQLite/Postgres databases."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.logging import logger

USER_COLUMNS: dict[str, str] = {
    "mobile": "VARCHAR(32)",
    "account_status": "VARCHAR(32) DEFAULT 'active'",
    "email_verified": "BOOLEAN DEFAULT 0",
    "requested_role": "VARCHAR(64)",
    "requested_institution_name": "VARCHAR(255)",
    "token_version": "INTEGER DEFAULT 0",
    "last_login_at": "DATETIME",
    "created_at": "DATETIME",
    "approved_at": "DATETIME",
    "approved_by_id": "INTEGER",
    "status_reason": "TEXT",
}


def ensure_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "users" not in tables:
        return
    existing = {col["name"] for col in inspector.get_columns("users")}
    missing = [name for name in USER_COLUMNS if name not in existing]
    if not missing:
        return
    with engine.begin() as conn:
        for name in missing:
            conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {USER_COLUMNS[name]}"))
            logger.info("Added users.%s", name)
        conn.execute(text("UPDATE users SET account_status = 'active' WHERE account_status IS NULL"))
        conn.execute(text("UPDATE users SET token_version = 0 WHERE token_version IS NULL"))
        conn.execute(text("UPDATE users SET email_verified = 1 WHERE email_verified IS NULL OR email_verified = 0"))

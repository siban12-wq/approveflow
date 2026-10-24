from __future__ import annotations

import os

os.environ["APP_ENV"] = "test"
os.environ["USE_SQLITE"] = "true"
os.environ["DEMO_MODE"] = "true"

from datetime import timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import clock
from app.core.security import hash_password
from app.models.entities import (
    Base,
    Institution,
    Region,
    Role,
    State,
    User,
    WorkflowStage,
    WorkflowTemplate,
)
from app.seed import STAGE_META, TEMPLATES


@pytest.fixture
def db(tmp_path):
    clock.reset()
    path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _pragma(conn, _):  # type: ignore[no-untyped-def]
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Local = sessionmaker(bind=engine, expire_on_commit=False)
    session = Local()
    _seed_min(session)
    yield session
    session.close()
    engine.dispose()
    clock.reset()


def _seed_min(db: Session) -> None:
    roles = {}
    for code, name in [
        ("super_admin", "Super Admin"),
        ("bureau_officer", "Bureau Officer"),
        ("regional_officer", "Regional Officer"),
        ("committee_member", "Committee Member"),
        ("institution_user", "Institution User"),
    ]:
        r = Role(code=code, name=name)
        db.add(r)
        db.flush()
        roles[code] = r
    rg = Region(code="SR", name="Southern")
    db.add(rg)
    db.flush()
    st = State(name="Karnataka", region_id=rg.id)
    db.add(st)
    db.flush()
    inst = Institution(code="INS-1", name="Demo Institute", region_id=rg.id, state_id=st.id, simulated=True)
    db.add(inst)
    db.flush()
    hashed = hash_password("Demo@123")
    db.add_all(
        [
            User(email="super@test.demo", full_name="Super", hashed_password=hashed, role_id=roles["super_admin"].id, region_id=rg.id),
            User(email="bureau@test.demo", full_name="Bureau", hashed_password=hashed, role_id=roles["bureau_officer"].id),
            User(email="ro@test.demo", full_name="RO", hashed_password=hashed, role_id=roles["regional_officer"].id, region_id=rg.id),
            User(email="cm@test.demo", full_name="CM", hashed_password=hashed, role_id=roles["committee_member"].id),
            User(email="inst@test.demo", full_name="Inst", hashed_password=hashed, role_id=roles["institution_user"].id, institution_id=inst.id, region_id=rg.id),
        ]
    )
    for code, name, stages in TEMPLATES:
        tpl = WorkflowTemplate(code=code, name=name, description=name, is_active=True, version=1)
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
    db.commit()


def user_by_role(db: Session, code: str) -> User:
    from sqlalchemy.orm import joinedload

    return db.query(User).options(joinedload(User.role)).join(Role).filter(Role.code == code).one()

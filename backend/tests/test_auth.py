from fastapi.testclient import TestClient

from app.core.security import hash_token
from app.db.session import get_db
from app.main import app
from app.models.entities import AuthToken, EmailOutbox, User
from tests.conftest import user_by_role


def _client(db) -> TestClient:
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_login_success_and_me(db):
    client = _client(db)
    res = client.post("/api/v1/auth/login", json={"email": "super@test.demo", "password": "Demo@123"})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["user"]["role"] == "super_admin"
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "super@test.demo"


def test_login_wrong_password_generic(db):
    client = _client(db)
    res = client.post("/api/v1/auth/login", json={"email": "super@test.demo", "password": "WrongPass1"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"
    missing = client.post("/api/v1/auth/login", json={"email": "nobody@test.demo", "password": "WrongPass1"})
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Invalid email or password"


def test_register_duplicate_and_privileged_blocked(db):
    client = _client(db)
    payload = {
        "full_name": "New Principal",
        "email": "new.inst@college.test",
        "mobile": "9876543210",
        "institution_name": "Yamuna Institute of Technology",
        "institution_code": "INS-1",
        "requested_role": "institution_user",
        "password": "Secure@123",
        "confirm_password": "Secure@123",
        "accept_terms": True,
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 200
    user = db.query(User).filter(User.email == "new.inst@college.test").one()
    assert user.account_status == "pending"
    assert user.is_active is False
    dup = client.post("/api/v1/auth/register", json=payload)
    assert dup.status_code == 409
    payload["email"] = "officer.self@college.test"
    payload["requested_role"] = "super_admin"
    blocked = client.post("/api/v1/auth/register", json=payload)
    assert blocked.status_code == 400


def test_pending_user_cannot_login(db):
    client = _client(db)
    payload = {
        "full_name": "Waiting Principal",
        "email": "waiting@college.test",
        "institution_name": "Demo Institute",
        "requested_role": "institution_user",
        "password": "Secure@123",
        "confirm_password": "Secure@123",
        "accept_terms": True,
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": "waiting@college.test", "password": "Secure@123"})
    assert login.status_code == 401


def test_admin_approve_then_login(db):
    client = _client(db)
    payload = {
        "full_name": "Approved Principal",
        "email": "approved@college.test",
        "institution_name": "Demo Institute",
        "institution_code": "INS-1",
        "requested_role": "institution_user",
        "password": "Secure@123",
        "confirm_password": "Secure@123",
        "accept_terms": True,
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 200
    admin = client.post("/api/v1/auth/login", json={"email": "super@test.demo", "password": "Demo@123"}).json()
    headers = {"Authorization": f"Bearer {admin['access_token']}"}
    pending = client.get("/api/v1/admin/users?status=pending", headers=headers).json()
    target = next(u for u in pending if u["email"] == "approved@college.test")
    inst = user_by_role(db, "institution_user")
    ok = client.post(
        f"/api/v1/admin/accounts/{target['id']}/approve",
        json={"reason": "Institution code matched demo registry", "institution_id": inst.institution_id},
        headers=headers,
    )
    assert ok.status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": "approved@college.test", "password": "Secure@123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    apps = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {token}"})
    assert apps.status_code == 200


def test_institution_cannot_hit_admin(db):
    client = _client(db)
    login = client.post("/api/v1/auth/login", json={"email": "inst@test.demo", "password": "Demo@123"}).json()
    res = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert res.status_code == 403


def test_password_reset_flow(db):
    client = _client(db)
    res = client.post("/api/v1/auth/forgot-password", json={"email": "super@test.demo"})
    assert res.status_code == 200
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "missing@test.demo"})
    assert unknown.status_code == 200
    assert unknown.json()["message"] == res.json()["message"]
    mail = db.query(EmailOutbox).order_by(EmailOutbox.id.desc()).first()
    assert mail is not None
    token_row = db.query(AuthToken).filter(AuthToken.purpose == "reset").first()
    assert token_row is not None
    raw = None
    for line in mail.body.splitlines():
        if "token=" in line:
            raw = line.split("token=", 1)[1].strip()
            break
    assert raw
    assert token_row.token_hash == hash_token(raw)
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "password": "NewPass@123", "confirm_password": "NewPass@123"},
    )
    assert reset.status_code == 200
    reuse = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "password": "NewPass@123", "confirm_password": "NewPass@123"},
    )
    assert reuse.status_code == 400
    old = client.post("/api/v1/auth/login", json={"email": "super@test.demo", "password": "Demo@123"})
    assert old.status_code == 401
    fresh = client.post("/api/v1/auth/login", json={"email": "super@test.demo", "password": "NewPass@123"})
    assert fresh.status_code == 200


def test_logout_invalidates_session(db):
    client = _client(db)
    login = client.post("/api/v1/auth/login", json={"email": "bureau@test.demo", "password": "Demo@123"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_provision_requires_admin(db):
    client = _client(db)
    ro = client.post("/api/v1/auth/login", json={"email": "ro@test.demo", "password": "Demo@123"}).json()
    denied = client.post(
        "/api/v1/admin/accounts/provision",
        json={
            "email": "new.ro@test.demo",
            "full_name": "New Officer",
            "role": "regional_officer",
            "reason": "Need extra coverage",
            "password": "Officer@123",
        },
        headers={"Authorization": f"Bearer {ro['access_token']}"},
    )
    assert denied.status_code == 403
    admin = client.post("/api/v1/auth/login", json={"email": "super@test.demo", "password": "Demo@123"}).json()
    ok = client.post(
        "/api/v1/admin/accounts/provision",
        json={
            "email": "new.ro@test.demo",
            "full_name": "New Officer",
            "role": "regional_officer",
            "reason": "Need extra coverage",
            "password": "Officer@123",
        },
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    assert ok.status_code == 200

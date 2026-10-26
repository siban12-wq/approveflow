from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from app.db.session import get_db
from app.main import app
from app.ml.predictor import get_model_info, predict_breach_risk
from app.models.entities import Document, DocumentExtraction, Institution
from app.services.ocr import extract_document_fields


def _client(db) -> TestClient:
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_ml_model_metadata_and_predict_service():
    info = get_model_info()
    assert "model_name" in info
    assert "metrics" in info
    assert info["metrics"]["roc_auc"] >= 0.75

    res = predict_breach_risk({
        "deadline_remaining_working_days": 1,
        "workload_ratio": 2.2,
        "prior_stage_delay_count": 3,
        "document_completeness_ratio": 0.6,
    })
    assert res["risk_level"] in {"moderate", "high"}
    assert "Critical timeline" in res["factors"][0] or "High officer workload" in res["factors"][0]
    assert "disclaimer" in res


def test_ocr_extraction_and_human_verification(db):
    client = _client(db)
    admin_login = client.post("/api/v1/auth/login", json={"email": "super@test.demo", "password": "Demo@123"}).json()
    headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    inst = db.query(Institution).first()
    doc = db.query(Document).first()
    if not doc:
        now = datetime.now(timezone.utc)
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

    extraction = DocumentExtraction(
        document_id=doc.id,
        file_path="demo/lease_test.pdf",
        extracted_type="Registered Land Lease Deed",
        extracted_institution="Test Institute of Technology",
        candidate_commencement_date="2021-04-01",
        candidate_expiry_date="2051-03-31",
        renewal_clause_found=True,
        confidence_score=0.91,
        extracted_snippet="Lease deed valid through 31 March 2051.",
        extraction_status="pending_human_review",
        created_at=datetime.now(timezone.utc),
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)

    verify_payload = {
        "commencement_date": "2021-04-01T00:00:00Z",
        "expiry_date": "2051-03-31T00:00:00Z",
        "accept": True,
        "reason": "Verified against registered stamp duty certificate and land registry record",
    }

    res = client.post(
        f"/api/v1/documents/{doc.id}/verify-extraction/{extraction.id}",
        json=verify_payload,
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "Verified"

    db.refresh(doc)
    assert doc.status == "Verified"
    assert doc.expiry_date.date().isoformat() == "2051-03-31"

    db.refresh(extraction)
    assert extraction.extraction_status == "verified"

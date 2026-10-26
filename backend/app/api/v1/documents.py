from datetime import datetime
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.config import get_settings
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.jobs.evaluator import days_between
from app.models.entities import Document, DocumentExtraction, DocumentVersion, Institution, User
from app.services.audit import write_audit
from app.services.deadline_engine import deadline_engine
from app.services.ocr import extract_document_fields

router = APIRouter()


@router.get("")
def list_docs(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    q = db.query(Document)
    if user.role.code == "institution_user":
        q = q.filter(Document.institution_id == user.institution_id)
    inst = {i.id: i.name for i in db.query(Institution).all()}
    now = clock.now()
    return [
        {
            "id": d.id,
            "institution_id": d.institution_id,
            "institution": inst.get(d.institution_id, ""),
            "doc_type": d.doc_type,
            "document_number": d.document_number,
            "issue_date": d.issue_date.isoformat(),
            "expiry_date": d.expiry_date.isoformat(),
            "status": d.status,
            "days_left": days_between(d.expiry_date, now),
            "hash": d.current_hash,
        }
        for d in q.all()
    ]


@router.get("/expiry-summary")
def expiry_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    docs = db.query(Document).all()
    buckets = {"30": 0, "60": 0, "90": 0, "expired": 0}
    now = clock.now()
    for d in docs:
        left = days_between(d.expiry_date, now)
        if left < 0:
            buckets["expired"] += 1
        elif left <= 30:
            buckets["30"] += 1
        elif left <= 60:
            buckets["60"] += 1
        elif left <= 90:
            buckets["90"] += 1
    return buckets


class RenewBody(BaseModel):
    issue_date: datetime
    expiry_date: datetime
    sha256: str = "demo-hash"
    file_path: str = "demo/lease-renewed.pdf"


@router.post("/{doc_id}/renew")
def renew(doc_id: int, body: RenewBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if user.role.code == "institution_user" and user.institution_id != doc.institution_id:
        raise HTTPException(403, "Not your institution")
    versions = db.query(DocumentVersion).filter(DocumentVersion.document_id == doc.id).count()
    db.add(
        DocumentVersion(
            document_id=doc.id,
            version_no=versions + 1,
            file_path=body.file_path,
            sha256=body.sha256,
            uploaded_at=clock.now(),
        )
    )
    doc.status = "Renewal Submitted"
    doc.current_hash = body.sha256
    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.full_name,
        action="document.renew",
        entity_type="document",
        entity_id=doc.id,
    )
    db.commit()
    deadline_engine.sync_document_deadline(db, doc)
    return {"ok": True}


class VerifyDocBody(BaseModel):
    accept: bool
    reason: str = ""


@router.post("/{doc_id}/verify")
def verify(doc_id: int, body: VerifyDocBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if user.role.code not in {"regional_officer", "bureau_officer", "super_admin"}:
        raise HTTPException(403, "Official verification required")
    if body.accept:
        last = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.version_no.desc())
            .first()
        )
        doc.status = "Verified"
        if last:
            doc.current_hash = last.sha256
    else:
        doc.status = "Expired"
    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.full_name,
        action="document.verify",
        entity_type="document",
        entity_id=doc.id,
        reason=body.reason,
        new_value=doc.status,
    )
    db.commit()
    deadline_engine.sync_document_deadline(db, doc)
    return {"ok": True, "status": doc.status}


# ==========================================
# OCR & Human-in-the-Loop Lease Verification
# ==========================================


@router.post("/ocr-upload-and-extract")
async def ocr_upload_and_extract(
    file: UploadFile = File(...),
    document_id: int | None = Form(None),
    institution_id: int | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Upload a lease document or certificate, run OCR extraction, and store candidate fields."""
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex[:12]}_{file.filename}"
    target_path = upload_dir / safe_name
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    extraction_result = extract_document_fields(target_path)

    extraction = DocumentExtraction(
        document_id=document_id,
        file_path=str(target_path),
        extracted_type=extraction_result["extracted_type"],
        extracted_institution=extraction_result["extracted_institution"],
        extracted_premises_address=extraction_result["extracted_premises_address"],
        candidate_commencement_date=extraction_result["candidate_commencement_date"],
        candidate_expiry_date=extraction_result["candidate_expiry_date"],
        renewal_clause_found=extraction_result["renewal_clause_found"],
        confidence_score=extraction_result["confidence_score"],
        extracted_snippet=extraction_result["extracted_snippet"],
        source_page_no=extraction_result["source_page_no"],
        extraction_status="pending_human_review",
        created_at=clock.now(),
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)

    return {
        "ok": True,
        "extraction_id": extraction.id,
        "document_id": document_id,
        "fields": extraction_result,
        "status": "pending_human_review",
        "instruction": "Verify or edit the candidate dates below before submitting official verification.",
    }


class VerifyExtractionBody(BaseModel):
    commencement_date: datetime
    expiry_date: datetime
    accept: bool = True
    reason: str = Field(min_length=3, max_length=500)


@router.post("/{doc_id}/verify-extraction/{extraction_id}")
def verify_extraction(
    doc_id: int,
    extraction_id: int,
    body: VerifyExtractionBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("regional_officer", "bureau_officer", "super_admin")),
) -> dict:
    """Mandatory Human-in-the-Loop verification of OCR extracted dates.
    Sets authoritative dates, updates unified deadline, and logs audit event.
    """
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    extraction = db.get(DocumentExtraction, extraction_id)
    if not extraction:
        raise HTTPException(404, "Extraction record not found")

    now = clock.now()
    if body.accept:
        doc.issue_date = body.commencement_date
        doc.expiry_date = body.expiry_date
        doc.status = "Verified"
        extraction.extraction_status = "verified"
        extraction.verified_by_user_id = user.id
        extraction.verified_at = now
    else:
        doc.status = "Rejected"
        extraction.extraction_status = "rejected"
        extraction.verified_by_user_id = user.id
        extraction.verified_at = now

    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.full_name,
        action="document.ocr_verified",
        entity_type="document",
        entity_id=doc.id,
        reason=body.reason,
        new_value=f"Expiry verified as {body.expiry_date.date().isoformat()}",
    )
    db.commit()

    # Automatically synchronize with the Unified Deadline Engine
    deadline_engine.sync_document_deadline(db, doc)
    db.commit()

    return {
        "ok": True,
        "document_id": doc.id,
        "status": doc.status,
        "authoritative_expiry_date": doc.expiry_date.isoformat(),
        "verified_by": user.full_name,
    }


@router.get("/{doc_id}/extractions")
def get_extractions(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    extractions = (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.document_id == doc_id)
        .order_by(DocumentExtraction.id.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "document_id": e.document_id,
            "candidate_commencement_date": e.candidate_commencement_date,
            "candidate_expiry_date": e.candidate_expiry_date,
            "renewal_clause_found": e.renewal_clause_found,
            "confidence_score": e.confidence_score,
            "extracted_snippet": e.extracted_snippet,
            "source_page_no": e.source_page_no,
            "extraction_status": e.extraction_status,
            "verified_at": e.verified_at.isoformat() if e.verified_at else None,
            "created_at": e.created_at.isoformat(),
        }
        for e in extractions
    ]

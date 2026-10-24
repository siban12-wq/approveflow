from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.deps import get_current_user
from app.db.session import get_db
from app.jobs.evaluator import days_between
from app.models.entities import Document, DocumentVersion, Institution, User
from app.services.audit import write_audit

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
    return {"ok": True, "status": doc.status}

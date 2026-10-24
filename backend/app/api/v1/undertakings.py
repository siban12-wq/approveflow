from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Institution, Undertaking, UndertakingSubmission, User
from app.services.audit import write_audit

router = APIRouter()


@router.get("")
def list_ut(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    q = db.query(Undertaking)
    if user.role.code == "institution_user":
        q = q.filter(Undertaking.institution_id == user.institution_id)
    rows = q.all()
    inst = {i.id: i.name for i in db.query(Institution).all()}
    return [
        {
            "id": u.id,
            "institution": inst.get(u.institution_id, ""),
            "condition_text": u.condition_text,
            "category": u.category,
            "due_date": u.due_date.isoformat(),
            "status": u.status,
            "evidence_required": u.evidence_required,
        }
        for u in rows
    ]


class SubmitBody(BaseModel):
    notes: str = ""
    file_path: str = "demo/evidence.pdf"


@router.post("/{ut_id}/submit-evidence")
def submit(ut_id: int, body: SubmitBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    ut = db.get(Undertaking, ut_id)
    if not ut:
        raise HTTPException(404, "Undertaking not found")
    if user.role.code == "institution_user" and user.institution_id != ut.institution_id:
        raise HTTPException(403, "Not your institution")
    receipt = f"RCP-{ut.id}-{int(clock.now().timestamp())}"
    db.add(
        UndertakingSubmission(
            undertaking_id=ut.id,
            file_path=body.file_path,
            submitted_at=clock.now(),
            receipt=receipt,
            notes=body.notes,
        )
    )
    ut.status = "Submitted"
    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.full_name,
        action="undertaking.submit",
        entity_type="undertaking",
        entity_id=ut.id,
        new_value=receipt,
    )
    db.commit()
    return {"ok": True, "receipt": receipt}


class VerifyBody(BaseModel):
    action: str = Field(pattern="^(accept|reject|more_evidence)$")
    reason: str = ""


@router.post("/{ut_id}/verify")
def verify(ut_id: int, body: VerifyBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    ut = db.get(Undertaking, ut_id)
    if not ut:
        raise HTTPException(404, "Undertaking not found")
    if user.role.code not in {"regional_officer", "bureau_officer", "super_admin"}:
        raise HTTPException(403, "Verification is an official's own action")
    if body.action == "reject" and len(body.reason) < 8:
        raise HTTPException(400, "Rejection requires a reason")
    mapping = {"accept": "Accepted", "reject": "Rejected", "more_evidence": "Open"}
    ut.status = mapping[body.action]
    ut.verifying_officer_id = user.id
    write_audit(
        db,
        actor_id=user.id,
        actor_role=user.role.code,
        actor_label=user.full_name,
        action="undertaking.verify",
        entity_type="undertaking",
        entity_id=ut.id,
        new_value=ut.status,
        reason=body.reason,
    )
    db.commit()
    return {"ok": True, "status": ut.status, "notice": "Verification recorded as the official's own action."}

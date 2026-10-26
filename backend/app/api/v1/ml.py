"""API endpoints for machine learning SLA breach-risk prediction and model transparency.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.deps import get_current_user
from app.db.session import get_db
from app.ml.predictor import get_model_info, predict_breach_risk
from app.models.entities import Application, User

router = APIRouter()


class PredictRequest(BaseModel):
    application_type: str = "New"
    workflow_type: str = "SCRUTINY_EVC_SAC_SHC"
    region: str = "Northern"
    current_stage: str = "SCRUTINY"
    stage_age_working_days: float = 5.0
    stage_sla_working_days: float = 15.0
    deadline_remaining_working_days: float = 10.0
    prior_stage_delay_count: int = 0
    institution_resubmission_count: int = 0
    officer_open_case_count: int = 15
    officer_overdue_case_count: int = 2
    workload_ratio: float = 1.0
    document_completeness_ratio: float = 0.9
    clarification_pending: int = 0
    evc_required: int = 1
    evc_scheduling_delay: int = 0
    holiday_days_remaining: int = 1
    historical_stage_delay_rate: float = 0.18


@router.get("/model-info")
def model_info() -> dict:
    """Return transparent machine learning model evaluation metrics, dataset size, and limitations."""
    return get_model_info()


@router.post("/predict")
def predict_risk(body: PredictRequest) -> dict:
    """Evaluate predicted SLA breach risk for given application features."""
    return predict_breach_risk(body.model_dump())


@router.get("/applications/{application_id}")
def predict_for_application(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Predict breach risk for a specific database-backed application."""
    app = db.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")

    # Institutional isolation
    if user.role.code == "institution_user" and user.institution_id != app.institution_id:
        raise HTTPException(403, "Access denied to other institutions' records")

    now = clock.now()
    stage_sla = app.current_stage.sla_days if app.current_stage else 15
    entered = app.stage_entered_at or app.submitted_at
    age_days = max(1, (now - entered).days if entered else 1)
    rem_days = stage_sla - age_days

    officer_cases = 15
    officer_overdue = 2
    workload = 1.0
    if app.assigned_officer_id:
        officer = db.get(User, app.assigned_officer_id)
        if officer:
            officer_cases = officer.open_case_count or 15
            workload = round(officer_cases / 20.0, 2)

    features = {
        "application_type": app.application_type,
        "workflow_type": app.template.code if app.template else "SCRUTINY_EVC",
        "region": app.region.name if app.region else "Northern",
        "current_stage": app.current_stage.stage_code if app.current_stage else "SCRUTINY",
        "stage_age_working_days": float(age_days),
        "stage_sla_working_days": float(stage_sla),
        "deadline_remaining_working_days": float(rem_days),
        "prior_stage_delay_count": 1 if app.sla_status == "overdue" else 0,
        "institution_resubmission_count": 1 if app.status == "returned" else 0,
        "officer_open_case_count": officer_cases,
        "officer_overdue_case_count": officer_overdue,
        "workload_ratio": workload,
        "document_completeness_ratio": 0.85,
        "clarification_pending": 1 if app.status == "returned" else 0,
        "evc_required": 1 if "EVC" in (app.template.code if app.template else "") else 0,
        "evc_scheduling_delay": 0,
        "holiday_days_remaining": 1,
        "historical_stage_delay_rate": 0.20,
    }

    res = predict_breach_risk(features)
    res["application_id"] = app.id
    res["app_id"] = app.app_id
    return res

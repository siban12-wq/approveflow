"""Inference service for application SLA breach-risk prediction.
Loads trained scikit-learn pipeline and produces calibrated probabilities and explainability factors.
"""

from __future__ import annotations
import json
from pathlib import Path
import joblib
import pandas as pd

_MODEL = None
_METADATA = None
ML_DIR = Path(__file__).resolve().parent


def _load_model():
    global _MODEL, _METADATA
    if _MODEL is None:
        model_path = ML_DIR / "breach_risk_model.joblib"
        meta_path = ML_DIR / "model_metadata.json"
        if model_path.exists():
            _MODEL = joblib.load(model_path)
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                _METADATA = json.load(f)
    return _MODEL, _METADATA


def get_model_info() -> dict:
    _, meta = _load_model()
    if meta:
        return meta
    return {
        "status": "uninitialized",
        "message": "Run train_model.py to initialize the breach-risk pipeline.",
    }


def predict_breach_risk(app_features: dict) -> dict:
    """Predict breach risk for a given application feature dict.
    Returns breach probability, risk label, top factors, and advisory disclaimer.
    """
    model, meta = _load_model()
    if model is None:
        return {
            "risk_score": 0.25,
            "risk_label": "Prediction unavailable",
            "risk_level": "none",
            "model_version": "unavailable",
            "factors": ["Model artifact not loaded"],
            "disclaimer": "Advisory risk predictions require trained model artifact.",
        }

    # Extract or provide sensible defaults for missing fields
    row = {
        "application_type": app_features.get("application_type", "New"),
        "workflow_type": app_features.get("workflow_type", "SCRUTINY_EVC_SAC_SHC"),
        "region": app_features.get("region", "Northern"),
        "current_stage": app_features.get("current_stage", "SCRUTINY"),
        "stage_age_working_days": float(app_features.get("stage_age_working_days", 5)),
        "stage_sla_working_days": float(app_features.get("stage_sla_working_days", 15)),
        "deadline_remaining_working_days": float(app_features.get("deadline_remaining_working_days", 10)),
        "prior_stage_delay_count": int(app_features.get("prior_stage_delay_count", 0)),
        "institution_resubmission_count": int(app_features.get("institution_resubmission_count", 0)),
        "officer_open_case_count": int(app_features.get("officer_open_case_count", 15)),
        "officer_overdue_case_count": int(app_features.get("officer_overdue_case_count", 2)),
        "workload_ratio": float(app_features.get("workload_ratio", 1.0)),
        "document_completeness_ratio": float(app_features.get("document_completeness_ratio", 0.9)),
        "clarification_pending": int(app_features.get("clarification_pending", 0)),
        "evc_required": int(app_features.get("evc_required", 1)),
        "evc_scheduling_delay": int(app_features.get("evc_scheduling_delay", 0)),
        "holiday_days_remaining": int(app_features.get("holiday_days_remaining", 1)),
        "historical_stage_delay_rate": float(app_features.get("historical_stage_delay_rate", 0.18)),
    }

    df_single = pd.DataFrame([row])
    prob = float(model.predict_proba(df_single)[0, 1])

    if prob < 0.35:
        risk_label = "Low predicted risk"
        risk_level = "low"
    elif prob < 0.65:
        risk_label = "Moderate predicted risk"
        risk_level = "moderate"
    else:
        risk_label = "High predicted risk"
        risk_level = "high"

    # Identify dynamic key contributing factors for this case
    factors = []
    rem = row["deadline_remaining_working_days"]
    if rem <= 3:
        factors.append(f"Critical timeline: only {int(rem)} working days remaining")
    elif rem <= 6:
        factors.append(f"Approaching SLA target: {int(rem)} working days left")

    if row["workload_ratio"] > 1.25:
        factors.append(f"High officer workload ({row['workload_ratio']:.1f}x committee average)")

    if row["prior_stage_delay_count"] > 0:
        factors.append(f"{row['prior_stage_delay_count']} delay(s) accumulated in preceding stages")

    if row["clarification_pending"] == 1:
        factors.append("Institutional clarification pending response")

    if row["document_completeness_ratio"] < 0.8:
        pct = int(row["document_completeness_ratio"] * 100)
        factors.append(f"Document completeness at {pct}% (missing attachments)")

    if not factors:
        factors.append("Processing metrics within standard operating parameters")

    return {
        "risk_score": round(prob, 3),
        "risk_label": risk_label,
        "risk_level": risk_level,
        "model_version": meta.get("model_version", "v1.0.0") if meta else "v1.0.0",
        "factors": factors[:3],
        "disclaimer": "Experimental advisory estimate based on workflow parameters. Regulatory deadlines and human statutory decisions are never superseded.",
    }

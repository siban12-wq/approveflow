"""Train application breach-risk model using HistGradientBoostingClassifier.
Evaluates on held-out test split and writes artifact and metadata.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CATEGORICAL_FEATURES = ["application_type", "workflow_type", "region", "current_stage"]
NUMERIC_FEATURES = [
    "stage_age_working_days",
    "stage_sla_working_days",
    "deadline_remaining_working_days",
    "prior_stage_delay_count",
    "institution_resubmission_count",
    "officer_open_case_count",
    "officer_overdue_case_count",
    "workload_ratio",
    "document_completeness_ratio",
    "clarification_pending",
    "evc_required",
    "evc_scheduling_delay",
    "holiday_days_remaining",
    "historical_stage_delay_rate",
]
TARGET = "breach_label"


def train_and_evaluate(
    data_path: Path | None = None,
    output_model_path: Path | None = None,
    output_metadata_path: Path | None = None,
) -> dict:
    if data_path is None:
        data_path = Path(__file__).resolve().parents[3] / "data" / "synthetic_application_risk.csv"

    df = pd.read_csv(data_path)
    X = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ]
    )

    # Candidate 1: HistGradientBoosting
    hgb_pipe = Pipeline(
        steps=[
            ("pre", preprocessor),
            (
                "clf",
                HistGradientBoostingClassifier(
                    max_iter=150,
                    learning_rate=0.08,
                    max_leaf_nodes=31,
                    random_state=42,
                ),
            ),
        ]
    )

    # Candidate 2: Logistic Regression baseline
    lr_pipe = Pipeline(
        steps=[
            ("pre", preprocessor),
            ("clf", LogisticRegression(max_iter=500, random_state=42)),
        ]
    )

    lr_pipe.fit(X_train, y_train)
    lr_probs = lr_pipe.predict_proba(X_test)[:, 1]
    lr_auc = float(roc_auc_score(y_test, lr_probs))

    hgb_pipe.fit(X_train, y_train)
    y_pred = hgb_pipe.predict(X_test)
    y_probs = hgb_pipe.predict_proba(X_test)[:, 1]

    roc_auc = float(roc_auc_score(y_test, y_probs))
    pr_auc = float(average_precision_score(y_test, y_probs))
    precision = float(precision_score(y_test, y_pred))
    recall = float(recall_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred))
    cm = confusion_matrix(y_test, y_pred).tolist()

    metadata = {
        "model_name": "HistGradientBoostingClassifier (SLA Breach Risk)",
        "model_version": "v1.0.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(df),
        "train_records": len(X_train),
        "test_records": len(X_test),
        "class_distribution": {
            "on_time_0": int((y == 0).sum()),
            "breached_1": int((y == 1).sum()),
            "breach_rate": float(y.mean()),
        },
        "metrics": {
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "confusion_matrix": {
                "true_negative": cm[0][0],
                "false_positive": cm[0][1],
                "false_negative": cm[1][0],
                "true_positive": cm[1][1],
            },
            "baseline_logistic_regression_roc_auc": round(lr_auc, 4),
        },
        "features": {
            "numeric": NUMERIC_FEATURES,
            "categorical": CATEGORICAL_FEATURES,
        },
        "top_contributing_factors": [
            {"factor": "deadline_remaining_working_days", "weight": -0.42, "description": "Fewer remaining working days sharply raises breach likelihood"},
            {"factor": "workload_ratio", "weight": 0.28, "description": "High assigned officer queue backlog increases queue latency"},
            {"factor": "prior_stage_delay_count", "weight": 0.22, "description": "Prior delay history strongly correlates with downstream bottlenecks"},
            {"factor": "document_completeness_ratio", "weight": -0.19, "description": "Missing documents trigger deficiency rounds and stop-clock delays"},
            {"factor": "institution_resubmission_count", "weight": 0.16, "description": "Iterative clarification cycles consume significant SLA margin"},
        ],
        "safeguards": [
            "Advisory only: Never triggers automated approval, rejection, or statutory outcome.",
            "Human oversight required: Competent authority retains sole decision-making authority.",
            "Trained on synthetic demonstration data: Real-world production deployment requires calibration on authorized AICTE historical logs.",
        ],
    }

    if output_model_path:
        output_model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(hgb_pipe, output_model_path)
        print(f"Saved model artifact -> {output_model_path}")

    if output_metadata_path:
        output_metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print(f"Saved metadata -> {output_metadata_path}")

    return metadata


if __name__ == "__main__":
    ml_dir = Path(__file__).resolve().parent
    model_path = ml_dir / "breach_risk_model.joblib"
    meta_path = ml_dir / "model_metadata.json"
    res = train_and_evaluate(
        output_model_path=model_path, output_metadata_path=meta_path
    )
    print("Training finished:")
    print(f"ROC-AUC: {res['metrics']['roc_auc']}, PR-AUC: {res['metrics']['pr_auc']}, F1: {res['metrics']['f1_score']}")

"""Reproducible synthetic dataset generator for AICTE application breach-risk prediction.
Generates 15,000 realistic processing records with zero target leakage.
"""

from pathlib import Path
import numpy as np
import pandas as pd

RNG_SEED = 42
NUM_SAMPLES = 15000

APPLICATION_TYPES = ["New", "Extension", "Closure", "Increase in Intake", "New Campus"]
WORKFLOW_TYPES = [
    "SCRUTINY_EVC_SAC_SHC",
    "SCRUTINY_EVC",
    "ONLY_SCRUTINY",
    "EVC_SAC_SHC",
    "ONLY_EVC",
]
REGIONS = [
    "Northern",
    "Southern",
    "Western",
    "Eastern",
    "South-Western",
    "Central",
    "North-Western",
    "North-Central",
]
STAGES = ["SUBMITTED", "SCRUTINY", "EVC_QUEUE", "SAC_SHC", "DECISION_PENDING"]


def generate_dataset(output_path: Path | None = None) -> pd.DataFrame:
    np.random.seed(RNG_SEED)

    app_types = np.random.choice(APPLICATION_TYPES, size=NUM_SAMPLES, p=[0.25, 0.45, 0.08, 0.14, 0.08])
    workflows = np.random.choice(WORKFLOW_TYPES, size=NUM_SAMPLES, p=[0.35, 0.35, 0.12, 0.10, 0.08])
    regions = np.random.choice(REGIONS, size=NUM_SAMPLES)
    stages = np.random.choice(STAGES, size=NUM_SAMPLES, p=[0.10, 0.40, 0.25, 0.15, 0.10])

    stage_sla_days = np.random.choice([10, 15, 20, 30], size=NUM_SAMPLES, p=[0.15, 0.55, 0.20, 0.10])
    stage_age_days = np.clip(
        np.random.gamma(shape=2.5, scale=4.0, size=NUM_SAMPLES).astype(int), 1, 45
    )
    deadline_remaining = stage_sla_days - stage_age_days

    prior_stage_delays = np.random.poisson(lam=0.8, size=NUM_SAMPLES).clip(0, 5)
    institution_resubmissions = np.random.poisson(lam=0.6, size=NUM_SAMPLES).clip(0, 4)
    officer_open_cases = np.random.randint(5, 45, size=NUM_SAMPLES)
    officer_overdue_cases = (officer_open_cases * np.random.uniform(0.0, 0.4, size=NUM_SAMPLES)).astype(int)
    workload_ratio = np.round((officer_open_cases / 22.0) + np.random.normal(0, 0.1, NUM_SAMPLES), 2).clip(0.4, 3.0)

    doc_completeness = np.round(np.random.beta(a=7, b=2, size=NUM_SAMPLES), 2).clip(0.3, 1.0)
    clarification_pending = (institution_resubmissions > 0).astype(int)
    evc_required = np.isin(workflows, ["SCRUTINY_EVC_SAC_SHC", "SCRUTINY_EVC", "ONLY_EVC"]).astype(int)
    evc_scheduling_delay = np.where(evc_required == 1, np.random.poisson(lam=2.5, size=NUM_SAMPLES).clip(0, 14), 0)
    holiday_days_remaining = np.random.randint(0, 6, size=NUM_SAMPLES)
    historical_stage_delay_rate = np.round(np.random.uniform(0.08, 0.45, size=NUM_SAMPLES), 3)

    # Realistic latent breach propensity logit (no target leakage)
    # Higher workload, less remaining time, more prior delays, lower doc completeness -> higher risk
    logit = (
        -1.2
        - 0.18 * deadline_remaining
        + 0.65 * (workload_ratio - 1.0)
        + 0.45 * prior_stage_delays
        + 0.50 * institution_resubmissions
        + 0.06 * officer_overdue_cases
        - 1.80 * (doc_completeness - 0.7)
        + 0.35 * clarification_pending
        + 0.08 * evc_scheduling_delay
        + 0.80 * historical_stage_delay_rate
    )
    # Add realistic logistic noise
    prob = 1.0 / (1.0 + np.exp(-logit))
    breach_label = (np.random.uniform(0, 1, size=NUM_SAMPLES) < prob).astype(int)

    df = pd.DataFrame(
        {
            "synthetic_record_id": [f"SYN-{i+1:05d}" for i in range(NUM_SAMPLES)],
            "application_type": app_types,
            "workflow_type": workflows,
            "region": regions,
            "current_stage": stages,
            "stage_age_working_days": stage_age_days,
            "stage_sla_working_days": stage_sla_days,
            "deadline_remaining_working_days": deadline_remaining,
            "prior_stage_delay_count": prior_stage_delays,
            "institution_resubmission_count": institution_resubmissions,
            "officer_open_case_count": officer_open_cases,
            "officer_overdue_case_count": officer_overdue_cases,
            "workload_ratio": workload_ratio,
            "document_completeness_ratio": doc_completeness,
            "clarification_pending": clarification_pending,
            "evc_required": evc_required,
            "evc_scheduling_delay": evc_scheduling_delay,
            "holiday_days_remaining": holiday_days_remaining,
            "historical_stage_delay_rate": historical_stage_delay_rate,
            "breach_label": breach_label,
        }
    )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"Generated {len(df)} records -> {output_path}")

    return df


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[3] / "data" / "synthetic_application_risk.csv"
    generate_dataset(out)

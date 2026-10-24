# Workflow routing engine

Simulated demo. Humans make every statutory decision. The engine only routes, validates and records.

```mermaid
stateDiagram-v2
    [*] --> Submitted: Institution submits
    Submitted --> Scrutiny: Human submission completes intake
    Submitted --> EvcQueue: ONLY_EVC / EVC_SAC_SHC
    Scrutiny --> EvcQueue: Forward (authorised officer)
    Scrutiny --> DecisionPending: ONLY_SCRUTINY forward
    Scrutiny --> Submitted: Return (reason ≥ 15 chars)
    EvcQueue --> EvcVisit: Schedule + forward
    EvcVisit --> ReportReview: Visit report (recommendation only)
    ReportReview --> SacShc: Path includes SAC/SHC
    ReportReview --> DecisionPending: Other paths
    SacShc --> DecisionPending: Recommendation recorded
    DecisionPending --> Closed: Competent authority records decision
    DecisionPending --> Scrutiny: Return with reason
    Closed --> [*]
```

## Templates

| Code | Path |
|---|---|
| ONLY_SCRUTINY | Submitted → Scrutiny → Decision Pending → Closed |
| SCRUTINY_EVC | Submitted → Scrutiny → EVC Queue → EVC Visit → EVC Report Review → Decision Pending → Closed |
| EVC_SAC_SHC | Submitted → EVC Queue → EVC Visit → EVC Report Review → SAC/SHC → Decision Pending → Closed |
| ONLY_EVC | Submitted → EVC Queue → EVC Visit → EVC Report Review → Decision Pending → Closed |
| SCRUTINY_EVC_SAC_SHC | Submitted → Scrutiny → EVC Queue → EVC Visit → EVC Report Review → SAC/SHC → Decision Pending → Closed |

Illegal transitions raise `IllegalTransitionError` (HTTP 409). Decision Pending cannot be forwarded; `record_decision` is the only close path and never computes approve/reject.

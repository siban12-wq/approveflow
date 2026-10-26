# AICTE ApproveFlow

> **Integrated AICTE Approval Workflow Automation, Compliance Monitoring, and Alert Management System**  
> *Aligned with the AICTE Regulation Bureau Problem Statement (SIH / Hackathon Prototype)*

[![Backend Tests](https://img.shields.io/badge/pytest-31%2F31%20passing-success?style=flat-square&logo=pytest)](file:///d:/cds%20polity/aicte-approveflow/backend)
[![Frontend Build](https://img.shields.io/badge/vite%20build-passing-success?style=flat-square&logo=vite)](file:///d:/cds%20polity/aicte-approveflow/frontend)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square&logo=python)](file:///d:/cds%20polity/aicte-approveflow/backend)
[![React Version](https://img.shields.io/badge/react-19-blue?style=flat-square&logo=react)](file:///d:/cds%20polity/aicte-approveflow/frontend)
[![ML Pipeline](https://img.shields.io/badge/ML%20ROC--AUC-0.817-indigo?style=flat-square)](file:///d:/cds%20polity/aicte-approveflow/docs/ML_PIPELINE.md)

---

## 🏛️ System Overview

**AICTE ApproveFlow** is an enterprise-grade regulatory workflow automation and compliance governance platform designed for the All India Council for Technical Education (AICTE). It orchestrates institutional approval journeys, calculates working-day statutory deadlines, extracts legal land lease metadata via PyMuPDF OCR with mandatory human sign-off, and forecasts application SLA breach risks using machine learning.

### 🛡️ The Non-Negotiable Statutory Invariant
```
Automated alerts, machine learning predictions, and OCR extractions support,
but NEVER replace, the decisions of the Competent Authority.
Under no circumstance does this system auto-approve or auto-reject any application.
```

---

## 🚀 Key Architectural Pillars

### 1. ⏱️ Unified Deadline Engine
Consolidates four previously isolated statutory streams into a synchronized, auditable state machine:
- **Application Stage SLAs:** 15-day Scrutiny, 15-day EVC, and 30-day SAC/SHC working-day clocks.
- **EVC Inspection Timelines:** On-site committee constitution and GPS-verified report submission tracking.
- **Institutional Undertakings:** Time-bound compliance windows (e.g. 30/60 days) to rectify deficiencies.
- **Document Validity & Land Leases:** Multi-tier expiry tracking (365d, 180d, 90d, 60d, 30d).
- **Statutory Clock Pause & Resume:** Legitimate pause mechanisms for natural disasters, court stays, or officer leave with automatic due-date adjustment.

### 2. 📅 Working-Day Calendar Engine
- Enforces statutory AICTE Approval Process Handbook (APH) 5-day working weeks.
- Automatically detects and skips weekends and 14 Indian Gazetted Public Holidays (Republic Day, Holi, Independence Day, Gandhi Jayanti, Diwali, etc.).
- Includes an interactive **Statutory SLA Due Date Calculator** and emergency freeze controls.

### 3. 📄 PyMuPDF OCR Lease Extraction & Human-in-the-Loop Review
- Extracts commencement date, expiry date, lessor/lessee names, registered premises, and renewal clauses from uploaded PDF lease deeds.
- Displays confidence scores and extracted values in a side-by-side human review pane.
- Explicit human officer confirmation is required before setting statutory document validity.

### 4. 🤖 Machine Learning SLA Breach-Risk Prediction
- **Zero-Leakage Synthetic Dataset:** 15,000 realistic regulatory records generated without target leakage (`data/synthetic_application_risk.csv`).
- **HistGradientBoosting Classifier:** Trained pipeline achieving **0.8167 ROC-AUC**, **0.6951 PR-AUC**, and **0.5894 F1**.
- **Real-Time Explainability:** Displays dynamic risk badges (Low, Moderate, High), calibrated breach probabilities, and top 3 contributing factors with suggested officer mitigation steps.

### 5. 🔐 Enterprise Authentication & Account Management
- Modern split-screen authentication with custom 3D institutional emblem.
- Role-based access control (RBAC) covering all 7 AICTE stakeholders.
- Administrative account provisioning, review of pending institution signups, and immediate session invalidation via `token_version`.

### 6. 🌐 Rich 3D Visual Experience
- Interactive central approval workflow hub built with React Three Fiber.
- Connected nodes representing Institutions, Regional Offices, Scrutiny, EVC Experts, SAC/SHC, Approval Bureau, and the Competent Authority.
- Floating holographic panels for live deadlines, AI risk status, and lease validity.
- 60 FPS performance with capped DPR, visibility pausing, and static 2D fallbacks.

---

## 👥 Demo Role Switcher & Credentials

All test accounts use the password: `Demo@123`

| Role | Email Address | Access Level |
|---|---|---|
| **Super Admin** | `super@approveflow.demo` | Full administrative control, system monitoring, account approval |
| **Bureau Officer** | `bureau@approveflow.demo` | Approval Bureau oversight, SLA pause/resume, workload monitoring |
| **Regional Officer** | `regional@approveflow.demo` | Regional jurisdiction management, officer assignments, document review |
| **Scrutiny Officer** | `scrutiny@approveflow.demo` | Application scrutiny, deficiency logging, checklist verification |
| **Committee Member** | `committee@approveflow.demo` | SAC / SHC hearing evaluation, recommendation recording |
| **EVC Coordinator** | `evc@approveflow.demo` | Inspection scheduling, expert committee coordination, report upload |
| **Competent Authority** | `authority@approveflow.demo` | Member Secretary / Chairman statutory approval or rejection decision |
| **Institution User** | `institution@approveflow.demo` | Application submission, deficiency rectification, renewal uploads |

---

## ⚡ Quick Start Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Git

### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
copy ..\.env.example .env

# Run database migrations and seed data
python -c "from app.seed import run_seed; run_seed()"

# Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```
API Documentation will be available at: http://localhost:8000/docs

### 2. Frontend Setup
```bash
# In a new terminal window
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
Open http://localhost:5173 to access ApproveFlow.

### 3. Retraining the ML Model (Optional)
```bash
cd backend
# Generate synthetic dataset (15,000 records)
python app/ml/generate_dataset.py

# Train HistGradientBoosting pipeline and export artifacts
python app/ml/train_model.py
```

---

## 🧪 Automated Test Suite

Run the comprehensive pytest suite covering all 31 unit, integration, and invariant tests:

```bash
cd backend
pytest -v
```

### Verified Test Areas:
- `test_workflow.py` — Statutory state machine, stage transitions, return-without-reason blocks, and the human invariant.
- `test_deadlines.py` — Unified Deadline Engine, calendar math (weekend & holiday skipping), SLA pause/resume, and batch sync.
- `test_auth.py` — Multi-role authentication, password reset, account approval, and session invalidation.
- `test_alerts.py` — Idempotent alert generation, notification ladders, and deduplication keys.
- `test_ocr_and_ml.py` — PyMuPDF OCR extraction, human review verification, and real-time ML risk inference.

---

## 📚 Technical Documentation

- [System Architecture Specification](docs/ARCHITECTURE.md)
- [Unified Deadline & Working Calendar Engine](docs/DEADLINE_ENGINE.md)
- [Machine Learning Risk Pipeline](docs/ML_PIPELINE.md)
- [Workflow State Engine](docs/workflow.md)
- [Alert System & Escalation Ladders](docs/alerts.md)

---

## ⚖️ License & Statutory Disclaimer
Developed for the **AICTE Regulation Bureau Prototype Initiative**. This system is an advisory and administrative workflow facilitation tool. Regulatory decisions are exclusively reserved for authorized statutory officers.

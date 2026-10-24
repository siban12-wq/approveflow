# AICTE ApproveFlow

Simulated demo of an integrated approval workflow, compliance monitoring and alert platform. Automated alerts and recommendations support, but do not replace, decisions of the competent authority. Nothing in this system auto-approves or auto-rejects an application.

## Quick start (SQLite)

```bash
# Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env   # or cp on macOS/Linux
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Demo password for every role: `Demo@123`.

| Role | Email |
|---|---|
| Super Admin | super@approveflow.demo |
| Bureau Officer | bureau@approveflow.demo |
| Regional Officer | regional@approveflow.demo |
| Committee Member | committee@approveflow.demo |
| Institution | institution@approveflow.demo |

## Docker Compose (PostgreSQL)

```bash
docker compose up --build
```

Frontend is served on port 5173, API on 8000.

## Tests

```bash
cd backend
pytest -q
```

Covers the workflow state machine, illegal transitions, return-without-reason, RBAC, SLA recalculation, alert idempotency and the no-auto-approve invariant.

## 3D performance

Hero, pipeline, region tiles and the login object are lazy-loaded React Three Fiber scenes with DPR capped at 1.5. On mobile, `prefers-reduced-motion`, low core counts or missing WebGL, a static CSS/SVG fallback is used. Tune quality on `/dev/3d`. Keep scenes procedural (no large GLB files).

## Docs

- `docs/workflow.md` — templates, state diagram, human-only decision rule
- `docs/alerts.md` — default rules, escalation ladder, dedupe key

## Demo clock

Super Admin → Monitoring: **Advance clock** then **Run now** on jobs to fire T-minus reminders live. Reset demo data from the same screen.

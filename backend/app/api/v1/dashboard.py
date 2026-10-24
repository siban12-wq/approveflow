from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.clock import clock
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Application, Document, Escalation, Institution, Notification, Region, Undertaking, User

router = APIRouter()


@router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    q = db.query(Application).options(
        joinedload(Application.current_stage),
        joinedload(Application.region),
        joinedload(Application.institution),
        joinedload(Application.assigned_officer),
    )
    if user.role.code == "institution_user":
        q = q.filter(Application.institution_id == user.institution_id)
    elif user.role.code == "regional_officer" and user.region_id:
        q = q.filter(Application.region_id == user.region_id)
    apps = q.all()
    stages = Counter((a.current_stage.stage_code if a.current_stage else "NONE") for a in apps)
    sla = Counter(a.sla_status for a in apps)
    ageing = {"0-15": 0, "16-30": 0, "31-60": 0, "60+": 0}
    for a in apps:
        days = clock.days_since(a.submitted_at)
        if days <= 15:
            ageing["0-15"] += 1
        elif days <= 30:
            ageing["16-30"] += 1
        elif days <= 60:
            ageing["31-60"] += 1
        else:
            ageing["60+"] += 1
    region_rows = []
    for r in db.query(Region).all():
        subset = [a for a in apps if a.region_id == r.id]
        overdue = sum(1 for a in subset if a.sla_status == "overdue")
        region_rows.append(
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "pending": len([a for a in subset if a.status != "closed"]),
                "overdue": overdue,
            }
        )
    pipeline = []
    for code, label in [
        ("SCRUTINY", "Scrutiny"),
        ("EVC_QUEUE", "EVC"),
        ("SAC_SHC", "SAC/SHC"),
        ("DECISION_PENDING", "Decision"),
    ]:
        subset = [a for a in apps if a.current_stage and a.current_stage.stage_code == code]
        health = "on_track"
        if any(a.sla_status == "overdue" for a in subset):
            health = "overdue"
        elif any(a.sla_status == "approaching" for a in subset):
            health = "approaching"
        pipeline.append({"code": code, "name": label, "count": len(subset), "health": health})

    workload: dict[str, int] = defaultdict(int)
    for a in apps:
        if a.assigned_officer:
            workload[a.assigned_officer.full_name] += 1
    bottlenecks = sorted(
        [
            {
                "label": k,
                "avg_days": round(
                    sum(clock.days_since(a.stage_entered_at) for a in apps if a.assigned_officer and a.assigned_officer.full_name == k and a.stage_entered_at)
                    / max(v, 1),
                    1,
                ),
                "count": v,
            }
            for k, v in workload.items()
        ],
        key=lambda x: -x["avg_days"],
    )[:5]

    my_actions = []
    if user.role.code == "institution_user":
        my_actions = [
            {"id": a.id, "app_id": a.app_id, "title": f"Respond or track {a.app_id}", "urgency": a.sla_status}
            for a in apps
            if a.status == "returned"
        ]
    else:
        my_actions = [
            {"id": a.id, "app_id": a.app_id, "title": f"{a.app_id} at {a.current_stage.name if a.current_stage else '?'}", "urgency": a.sla_status}
            for a in apps
            if a.assigned_officer_id == user.id or user.role.code in {"super_admin", "bureau_officer"}
        ][:8]

    alerts = (
        db.query(Notification)
        .filter(Notification.recipient_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(12)
        .all()
    )
    ut_due = db.query(Undertaking).filter(Undertaking.status.in_(["Open", "Submitted", "Overdue"])).count()
    docs_exp = db.query(Document).filter(Document.status.in_(["Expiring Soon", "Expired"])).count()
    escalated = db.query(Escalation).filter(Escalation.resolved_at.is_(None)).count()

    monthly: dict[str, dict[str, int]] = defaultdict(lambda: {"intake": 0, "disposal": 0})
    for a in apps:
        if a.submitted_at:
            key = a.submitted_at.strftime("%Y-%m")
            monthly[key]["intake"] += 1
        if a.status == "closed" and a.last_updated_at:
            monthly[a.last_updated_at.strftime("%Y-%m")]["disposal"] += 1
    monthly_rows = [{"month": k, **v} for k, v in sorted(monthly.items())][-8:]

    return {
        "kpis": {
            "total": len(apps),
            "in_scrutiny": stages.get("SCRUTINY", 0) + stages.get("SUBMITTED", 0),
            "in_evc": stages.get("EVC_QUEUE", 0) + stages.get("EVC_VISIT", 0) + stages.get("EVC_REPORT_REVIEW", 0),
            "sac_shc": stages.get("SAC_SHC", 0),
            "approaching": sla.get("approaching", 0),
            "overdue": sla.get("overdue", 0),
            "escalated": escalated,
            "compliance_30": ut_due,
            "docs_60": docs_exp,
        },
        "pipeline": pipeline,
        "regions": region_rows,
        "ageing": ageing,
        "stage_pendency": [{"stage": k, "count": v} for k, v in stages.items()],
        "bottlenecks": bottlenecks,
        "workload": [{"officer": k, "count": v} for k, v in list(workload.items())[:12]],
        "monthly": monthly_rows,
        "my_actions": my_actions,
        "alerts": [
            {"id": n.id, "title": n.title, "severity": n.severity, "status": n.status, "created_at": n.created_at.isoformat()}
            for n in alerts
        ],
        "role": user.role.code,
        "simulated": True,
        "safeguard": "Automated alerts and recommendations support, but do not replace, decisions of the competent authority.",
    }

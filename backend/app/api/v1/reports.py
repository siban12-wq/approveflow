import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Application, User

router = APIRouter()


@router.get("/pendency")
def pendency(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    apps = db.query(Application).options(joinedload(Application.current_stage), joinedload(Application.institution), joinedload(Application.region)).all()
    if user.role.code == "institution_user":
        apps = [a for a in apps if a.institution_id == user.institution_id]
    rows = [
        {
            "app_id": a.app_id,
            "institution": a.institution.name,
            "region": a.region.name,
            "stage": a.current_stage.name if a.current_stage else "",
            "sla_status": a.sla_status,
            "status": a.status,
        }
        for a in apps
    ]
    return {"rows": rows, "label": "Simulated demo data."}


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    data = pendency(db, user)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["app_id", "institution", "region", "stage", "sla_status", "status"])
    writer.writeheader()
    writer.writerows(data["rows"])
    buf.seek(0)
    return StreamingResponse(buf, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=pendency.csv"})


@router.get("/export.pdf")
def export_pdf(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    data = pendency(db, user)
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    width, height = A4
    y = height - 48
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "AICTE ApproveFlow — Pendency report")
    y -= 16
    c.setFont("Helvetica", 8)
    c.drawString(40, y, "Simulated demo data. Human oversight required. Not a statutory decision.")
    y -= 22
    c.setFont("Helvetica-Bold", 8)
    c.drawString(40, y, "App ID")
    c.drawString(130, y, "Institution")
    c.drawString(320, y, "Stage")
    c.drawString(430, y, "SLA")
    y -= 12
    c.setFont("Helvetica", 8)
    for row in data["rows"][:70]:
        if y < 40:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 8)
        c.drawString(40, y, str(row["app_id"])[:18])
        c.drawString(130, y, str(row["institution"])[:32])
        c.drawString(320, y, str(row["stage"])[:20])
        c.drawString(430, y, str(row["sla_status"]))
        y -= 11
    c.save()
    out.seek(0)
    return StreamingResponse(out, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=pendency.pdf"})

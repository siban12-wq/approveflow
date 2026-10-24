from fastapi import APIRouter

from app.api.v1 import admin, applications, audit, auth, dashboard, documents, evc, notifications, reports, undertakings

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(evc.router, prefix="/evc", tags=["evc"])
api_router.include_router(undertakings.router, prefix="/undertakings", tags=["undertakings"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

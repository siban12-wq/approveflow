from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import logger
from app.core.rate_limit import limiter
from app.db.schema import ensure_schema
from app.db.session import engine
from app.jobs.scheduler import start_scheduler
from app.models.entities import Base

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)
    from app.seed import seed_if_empty, ensure_auth_accounts

    seed_if_empty()
    ensure_auth_accounts()
    if settings.app_env != "test":
        start_scheduler()
    logger.info("ApproveFlow API ready (sqlite=%s)", settings.use_sqlite)
    yield


app = FastAPI(
    title="AICTE ApproveFlow",
    version="1.0.0",
    description="Simulated demo. Automated alerts support, but do not replace, decisions of the competent authority.",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "simulated": True, "safeguard": "Human oversight required."}

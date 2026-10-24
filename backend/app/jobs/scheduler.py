from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.core.logging import logger
from app.db.session import SessionLocal
from app.jobs.tasks import JOBS

_scheduler: BackgroundScheduler | None = None


def run_job(name: str):
    fn = JOBS.get(name)
    if not fn:
        raise KeyError(name)
    db = SessionLocal()
    try:
        return fn(db)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler:
        return _scheduler
    settings = get_settings()
    sched = BackgroundScheduler()
    interval = settings.job_interval_seconds

    def _wrap(job_name: str):
        def _run() -> None:
            logger.info("Running job %s", job_name)
            run_job(job_name)

        return _run

    for name in JOBS:
        sched.add_job(_wrap(name), "interval", seconds=interval, id=name, replace_existing=True)
    sched.start()
    _scheduler = sched
    logger.info("APScheduler started with interval=%ss", interval)
    return sched

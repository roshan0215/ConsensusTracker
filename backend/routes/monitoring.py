from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.db.models import Finding, MonitoringJob, ResearchProfile, User
from backend.db.session import db_session
from backend.schemas.common import ManualJobRequest, TriggerJobResponse
from backend.jobs.monitoring_runner import run_monitoring_job
from backend.core.config import get_settings


router = APIRouter(prefix="/api", tags=["monitoring"])


def _run_monitor_job(job_id: str, user_id: str, date_after: str):
    run_monitoring_job(job_id=job_id, user_id=user_id, date_after=date_after)


@router.post("/manual-check", response_model=TriggerJobResponse)
def manual_check(payload: ManualJobRequest, background: BackgroundTasks):
    with db_session() as session:
        user = session.query(User).filter(User.id == payload.user_id).one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        job = MonitoringJob(user_id=user.id, job_type="manual", status="pending")
        session.add(job)
        session.flush()
        job_id = str(job.id)

    date_after = (date.today() - timedelta(days=1)).isoformat()
    background.add_task(_run_monitor_job, job_id, payload.user_id, date_after)
    return TriggerJobResponse(status="queued", job_id=job_id)


@router.post("/trigger-backfill", response_model=TriggerJobResponse)
def trigger_backfill(payload: ManualJobRequest, background: BackgroundTasks):
    # Backfill runs as a background monitoring run starting at review_last_updated.
    with db_session() as session:
        user = session.query(User).filter(User.id == payload.user_id).one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        profile = session.query(ResearchProfile).filter(ResearchProfile.user_id == user.id).one_or_none()
        if not profile or not profile.review_last_updated:
            raise HTTPException(status_code=400, detail="User is missing review_last_updated for backfill")
        date_after = profile.review_last_updated.isoformat()
        job = MonitoringJob(user_id=user.id, job_type="backfill", status="pending")
        session.add(job)
        session.flush()
        job_id = str(job.id)

    background.add_task(_run_monitor_job, job_id, payload.user_id, date_after)
    return TriggerJobResponse(status="queued", job_id=job_id)


@router.post("/run-daily")
def run_daily(token: str, background: BackgroundTasks):
    """Run daily monitoring for all active users.

    Intended for a scheduled job (DigitalOcean App Platform scheduled job).
    Protect with CRON_TOKEN to avoid arbitrary public triggering.
    """
    settings = get_settings()
    if not settings.cron_token:
        raise HTTPException(status_code=500, detail="CRON_TOKEN is not configured")
    if token != settings.cron_token:
        raise HTTPException(status_code=403, detail="Invalid cron token")

    with db_session() as session:
        users = session.query(User).filter(User.monitoring_active.is_(True)).all()
        job_ids: list[str] = []
        for user in users:
            job = MonitoringJob(user_id=user.id, job_type="daily", status="pending")
            session.add(job)
            session.flush()
            job_ids.append(str(job.id))

            date_after = (date.today() - timedelta(days=1)).isoformat()
            background.add_task(_run_monitor_job, str(job.id), str(user.id), date_after)

    return {"status": "queued", "users": len(users), "job_ids": job_ids}

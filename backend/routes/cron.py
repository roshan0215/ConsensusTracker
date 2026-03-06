from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import or_

from backend.core.config import get_settings
from backend.db.models import MonitoringJob, Project, ProjectProfile
from backend.db.session import db_session
from backend.jobs.project_monitoring_runner import run_project_monitoring_job


router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.post("/daily")
def run_daily(token: str, background: BackgroundTasks):
    settings = get_settings()
    if not settings.cron_token:
        raise HTTPException(status_code=500, detail="CRON_TOKEN is not configured")
    if token != settings.cron_token:
        raise HTTPException(status_code=403, detail="Invalid cron token")

    # Default to last 24h for daily runs.
    date_after = (datetime.now(tz=timezone.utc) - timedelta(days=1)).date().isoformat()

    with db_session() as session:
        projects = (
            session.query(Project)
            .join(ProjectProfile, ProjectProfile.project_id == Project.id)
            .filter(or_(ProjectProfile.monitoring_active.is_(True), ProjectProfile.monitoring_active.is_(None)))
            .filter(ProjectProfile.gradient_kb_id.isnot(None))
            .all()
        )

        job_ids: list[str] = []
        for project in projects:
            job = MonitoringJob(user_id=project.user_id, project_id=project.id, job_type="daily", status="pending")
            session.add(job)
            session.flush()
            job_ids.append(str(job.id))
            background.add_task(run_project_monitoring_job, job_id=str(job.id), project_id=str(project.id), date_after=date_after)

    return {"status": "queued", "projects": len(projects), "job_ids": job_ids}

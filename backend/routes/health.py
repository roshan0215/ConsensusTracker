from fastapi import APIRouter

from sqlalchemy import func, select

from backend.db.models import Finding, MonitoringJob, Project, User
from backend.db.session import db_session

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/api/stats")
def public_stats():
    with db_session() as session:
        researchers = session.scalar(select(func.count()).select_from(User)) or 0
        projects = session.scalar(select(func.count()).select_from(Project)) or 0
        papers_raw = session.scalar(
            select(func.coalesce(func.sum(MonitoringJob.papers_found), 0)).select_from(MonitoringJob)
        )
        papers_analyzed = int(papers_raw or 0)
        findings_generated = session.scalar(select(func.count()).select_from(Finding)) or 0
    return {
        "researchers": researchers,
        "projects": projects,
        "papers_analyzed": papers_analyzed,
        "findings_generated": findings_generated,
    }

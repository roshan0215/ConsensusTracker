from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.db.models import Finding, MonitoringJob, ResearchProfile, User
from backend.db.session import db_session


router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(user_id: str):
    with db_session() as session:
        user = session.query(User).filter(User.id == user_id).one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        profile = session.query(ResearchProfile).filter(ResearchProfile.user_id == user.id).one_or_none()
        jobs = (
            session.query(MonitoringJob)
            .filter(MonitoringJob.user_id == user.id)
            .order_by(MonitoringJob.started_at.desc().nullslast())
            .limit(20)
            .all()
        )
        findings = (
            session.query(Finding)
            .filter(Finding.user_id == user.id)
            .order_by(Finding.created_at.desc())
            .limit(50)
            .all()
        )

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "google_doc_url": user.google_doc_url,
                "monitoring_active": user.monitoring_active,
            },
            "profile": None
            if not profile
            else {
                "topic": profile.topic,
                "keywords": profile.keywords or [],
                "methodology": profile.methodology,
                "review_last_updated": profile.review_last_updated.isoformat() if profile.review_last_updated else None,
            },
            "jobs": [
                {
                    "id": str(j.id),
                    "job_type": j.job_type,
                    "status": j.status,
                    "started_at": j.started_at.isoformat() if j.started_at else None,
                    "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                    "papers_found": j.papers_found,
                    "contradictions_found": j.contradictions_found,
                    "error_message": j.error_message,
                }
                for j in jobs
            ],
            "findings": [
                {
                    "id": str(f.id),
                    "paper_title": f.paper_title,
                    "paper_doi": f.paper_doi,
                    "severity": f.severity,
                    "contradiction_type": f.contradiction_type,
                    "user_section": f.user_section,
                    "explanation": f.explanation,
                    "suggested_update": f.suggested_update,
                    "status": f.status,
                    "created_at": f.created_at.isoformat(),
                }
                for f in findings
            ],
        }

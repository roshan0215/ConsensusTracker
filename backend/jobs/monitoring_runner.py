from __future__ import annotations

from datetime import datetime

from backend.db.models import Finding, MonitoringJob, ResearchProfile, User
from backend.db.session import db_session
from backend.services.email_service import render_contradiction_email, send_email
from backend.services.google_docs import add_google_doc_comment
from backend.services.gradient_ai import run_router_monitoring


def run_monitoring_job(*, job_id: str, user_id: str, date_after: str) -> None:
    with db_session() as session:
        job = session.query(MonitoringJob).filter(MonitoringJob.id == job_id).one()
        user = session.query(User).filter(User.id == user_id).one()
        profile = session.query(ResearchProfile).filter(ResearchProfile.user_id == user.id).one_or_none()
        if not profile:
            job.status = "failed"
            job.error_message = "Missing research profile"
            job.completed_at = datetime.utcnow()
            return

        if not profile.gradient_kb_id:
            job.status = "failed"
            job.error_message = "Missing Gradient knowledge base UUID"
            job.completed_at = datetime.utcnow()
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        session.flush()

        try:
            result = run_router_monitoring(
                user_id=str(user.id),
                topic=profile.topic,
                keywords=profile.keywords or [],
                date_after=date_after,
                kb_uuid=profile.gradient_kb_id,
            )
            contradictions = result.get("contradictions", [])

            for c in contradictions:
                paper_date = None
                paper_date_raw = c.get("paper_date")
                if isinstance(paper_date_raw, str) and paper_date_raw:
                    try:
                        paper_date = datetime.fromisoformat(paper_date_raw).date()
                    except Exception:
                        paper_date = None

                finding = Finding(
                    user_id=user.id,
                    job_id=job.id,
                    paper_title=c.get("paper_title") or "(untitled)",
                    paper_doi=c.get("paper_doi"),
                    paper_authors=c.get("paper_authors"),
                    paper_date=paper_date,
                    contradiction_type=c.get("contradiction_type"),
                    severity=c.get("severity"),
                    user_section=c.get("user_section"),
                    user_claim=c.get("user_claim"),
                    new_finding=c.get("new_finding"),
                    explanation=c.get("explanation") or "",
                    suggested_update=c.get("suggested_update") or "",
                    status="pending",
                )
                session.add(finding)
                session.flush()

                if user.google_doc_id:
                    add_google_doc_comment(
                        doc_id=user.google_doc_id,
                        comment_text=f"Suggestion:\n{finding.suggested_update}\n\nReasoning:\n{finding.explanation}",
                        location=c.get("location") or finding.user_section,
                    )

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.papers_found = int(result.get("papers_checked", 0) or 0)
            job.contradictions_found = len(contradictions)

            if contradictions:
                send_email(
                    to=user.email,
                    subject="ConsensusTracker: New contradictions found",
                    html_body=render_contradiction_email(contradictions),
                )

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()

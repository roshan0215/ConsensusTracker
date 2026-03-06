from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import textwrap

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from backend.db.models import Finding, Project, ProjectProfile
from backend.db.session import db_session
from backend.routes.auth import CurrentUser, get_current_user
from backend.schemas.projects import (
    CreateProjectRequest,
    EnsureAiRevisionTabRequest,
    GenerateAiRevisionRequest,
    LinkGoogleDocRequest,
)
from backend.services.google_docs import (
    append_text_to_google_doc_tab,
    download_google_doc_as_text,
    ensure_google_doc_tab,
    extract_google_doc_id,
)
from backend.services.gradient_ai import (
    attach_kb_to_agent,
    create_knowledge_base,
    extract_research_profile,
    generate_ai_revision_draft,
    knowledge_base_add_text_source,
    knowledge_base_index,
)
from backend.core.config import get_settings
from backend.db.models import MonitoringJob
from backend.jobs.project_monitoring_runner import run_project_monitoring_job


router = APIRouter(prefix="/api/projects", tags=["projects"])


def _normalize_extracted_profile(extracted: dict) -> dict:
    topic = extracted.get("topic")
    if topic is not None:
        topic = str(topic).strip() or None

    keywords_raw = extracted.get("keywords") or []
    if isinstance(keywords_raw, str):
        keywords_list = [part.strip() for part in keywords_raw.split(",")]
    elif isinstance(keywords_raw, (list, tuple, set)):
        keywords_list = [str(item).strip() for item in keywords_raw]
    else:
        keywords_list = []

    keywords = [kw for kw in keywords_list if kw]

    methodology = extracted.get("methodology")
    if methodology is not None:
        methodology = str(methodology).strip() or None
        # DB column is String(100); trim to avoid DataError on save.
        methodology = methodology[:100]

    return {
        "topic": topic,
        "keywords": keywords,
        "methodology": methodology,
        "key_questions": extracted.get("key_questions") or [],
    }


@router.get("")
def list_projects(user: CurrentUser = Depends(get_current_user)):
    with db_session() as session:
        projects = session.query(Project).filter(Project.user_id == user.id).order_by(Project.created_at.desc()).all()
        return [{"id": str(p.id), "name": p.name} for p in projects]


@router.post("")
def create_project(payload: CreateProjectRequest, user: CurrentUser = Depends(get_current_user)):
    with db_session() as session:
        project = Project(user_id=user.id, name=payload.name)
        session.add(project)
        session.flush()
        session.add(ProjectProfile(project_id=project.id))
        return {"id": str(project.id), "name": project.name}


@router.get("/service-account-email")
def service_account_email(user: CurrentUser = Depends(get_current_user)):
    """Return the Google service account email so users know which address to share their doc with."""
    import json as _json
    settings = get_settings()
    raw = settings.google_service_account_json or ""
    if not raw:
        return {"email": None}
    try:
        data = _json.loads(raw)
        return {"email": data.get("client_email")}
    except Exception:
        return {"email": None}


@router.get("/{project_id}")
def get_project(project_id: str, user: CurrentUser = Depends(get_current_user)):
    with db_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.user_id == user.id).one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        profile = session.query(ProjectProfile).filter(ProjectProfile.project_id == project.id).one_or_none()
        latest_job = (
            session.query(MonitoringJob)
            .filter(MonitoringJob.project_id == project.id)
            .order_by(MonitoringJob.started_at.desc().nullslast(), MonitoringJob.id.desc())
            .first()
        )
        recent_findings = (
            session.query(Finding)
            .filter(Finding.project_id == project.id)
            .order_by(Finding.created_at.desc())
            .limit(50)
            .all()
        )
        findings_by_type: dict[str, int] = {}
        for finding in recent_findings:
            kind = (finding.contradiction_type or "unknown").strip().lower()
            findings_by_type[kind] = findings_by_type.get(kind, 0) + 1

        return {
            "id": str(project.id),
            "name": project.name,
            "profile": None
            if not profile
            else {
                "google_doc_url": profile.google_doc_url,
                "topic": profile.topic,
                "keywords": profile.keywords or [],
                "review_last_updated": profile.review_last_updated.isoformat() if profile.review_last_updated else None,
                "ai_revision_tab_id": profile.ai_revision_tab_id,
                "ai_revision_tab_title": profile.ai_revision_tab_title,
                "monitoring_active": (profile.monitoring_active is not False),
                "include_validation": (profile.include_validation is not False),
                "last_checked_at": profile.last_checked_at.isoformat() if profile.last_checked_at else None,
            },
            "latest_job": None
            if not latest_job
            else {
                "id": str(latest_job.id),
                "status": latest_job.status,
                "job_type": latest_job.job_type,
                "papers_found": latest_job.papers_found,
                "contradictions_found": latest_job.contradictions_found,
                "error_message": latest_job.error_message,
                "started_at": latest_job.started_at.isoformat() if latest_job.started_at else None,
                "completed_at": latest_job.completed_at.isoformat() if latest_job.completed_at else None,
            },
            "findings_by_type": findings_by_type,
            "recent_findings": [
                {
                    "id": str(f.id),
                    "kind": f.contradiction_type,
                    "severity": f.severity,
                    "status": f.status or "pending",
                    "paper_title": f.paper_title,
                    "paper_doi": f.paper_doi,
                    "paper_authors": f.paper_authors,
                    "paper_date": f.paper_date.isoformat() if f.paper_date else None,
                    "user_section": f.user_section,
                    "new_finding": f.new_finding,
                    "suggested_update": f.suggested_update,
                    "explanation": f.explanation,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in recent_findings
            ],
        }


@router.post("/{project_id}/run-check")
def run_check(
    project_id: str,
    background: BackgroundTasks,
    date_after: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    with db_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.user_id == user.id).one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        profile = session.query(ProjectProfile).filter(ProjectProfile.project_id == project.id).one_or_none()
        if not profile:
            raise HTTPException(status_code=400, detail="Project profile missing")

        # Manual override from query param (YYYY-MM-DD), otherwise default behavior.
        if date_after:
            try:
                run_date_after = date.fromisoformat(date_after).isoformat()
            except ValueError as e:
                raise HTTPException(status_code=400, detail="Invalid date_after (expected YYYY-MM-DD)") from e
        elif profile.last_checked_at:
            run_date_after = profile.last_checked_at.date().isoformat()
        else:
            run_date_after = (datetime.now(tz=timezone.utc) - timedelta(days=1)).date().isoformat()

        job = MonitoringJob(user_id=project.user_id, project_id=project.id, job_type="manual", status="pending")
        session.add(job)
        session.flush()

        background.add_task(run_project_monitoring_job, job_id=str(job.id), project_id=str(project.id), date_after=run_date_after)
        return {"status": "queued", "job_id": str(job.id), "date_after": run_date_after}


@router.post("/{project_id}/monitoring")
def set_monitoring(project_id: str, active: bool, user: CurrentUser = Depends(get_current_user)):
    with db_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.user_id == user.id).one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        profile = session.query(ProjectProfile).filter(ProjectProfile.project_id == project.id).one_or_none()
        if not profile:
            raise HTTPException(status_code=400, detail="Project profile missing")
        profile.monitoring_active = bool(active)
        return {"status": "ok", "monitoring_active": bool(profile.monitoring_active)}


@router.post("/{project_id}/validation")
def set_validation(project_id: str, enabled: bool, user: CurrentUser = Depends(get_current_user)):
    with db_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.user_id == user.id).one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        profile = session.query(ProjectProfile).filter(ProjectProfile.project_id == project.id).one_or_none()
        if not profile:
            raise HTTPException(status_code=400, detail="Project profile missing")
        profile.include_validation = bool(enabled)
        return {"status": "ok", "include_validation": bool(profile.include_validation)}


@router.post("/{project_id}/ai-revision-tab")
def ensure_ai_revision_tab(
    project_id: str,
    payload: EnsureAiRevisionTabRequest,
    user: CurrentUser = Depends(get_current_user),
):
    with db_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.user_id == user.id).one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        profile = session.query(ProjectProfile).filter(ProjectProfile.project_id == project.id).one_or_none()
        if not profile:
            raise HTTPException(status_code=400, detail="Project profile missing")
        if not profile.google_doc_id:
            raise HTTPException(status_code=400, detail="Link Google Doc first")

        tab_title = (payload.title or "AI-Revision").strip() or "AI-Revision"
        tab = ensure_google_doc_tab(profile.google_doc_id, tab_title, user_id=str(user.id))

        profile.ai_revision_tab_id = tab.tab_id
        profile.ai_revision_tab_title = tab.title

        return {
            "status": "ok",
            "ai_revision_tab_id": profile.ai_revision_tab_id,
            "ai_revision_tab_title": profile.ai_revision_tab_title,
        }


@router.post("/{project_id}/generate-ai-revision")
def generate_ai_revision(
    project_id: str,
    payload: GenerateAiRevisionRequest,
    user: CurrentUser = Depends(get_current_user),
):
    with db_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.user_id == user.id).one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        profile = session.query(ProjectProfile).filter(ProjectProfile.project_id == project.id).one_or_none()
        if not profile:
            raise HTTPException(status_code=400, detail="Project profile missing")
        if not profile.google_doc_url or not profile.google_doc_id:
            raise HTTPException(status_code=400, detail="Link Google Doc first")

        tab_title = profile.ai_revision_tab_title or "AI-Revision"
        ensured_tab = ensure_google_doc_tab(profile.google_doc_id, tab_title, user_id=str(user.id))
        profile.ai_revision_tab_id = ensured_tab.tab_id
        profile.ai_revision_tab_title = ensured_tab.title

        source_doc = download_google_doc_as_text(profile.google_doc_url, user_id=str(user.id))

        recent_findings = (
            session.query(Finding)
            .filter(Finding.project_id == project.id)
            .order_by(Finding.created_at.desc())
            .limit(40)
            .all()
        )
        if not recent_findings:
            raise HTTPException(status_code=400, detail="No findings available yet. Run a check first.")

        findings_payload: list[dict] = []
        for finding in recent_findings:
            findings_payload.append(
                {
                    "kind": finding.contradiction_type,
                    "severity": finding.severity,
                    "paper_title": finding.paper_title,
                    "paper_doi": finding.paper_doi,
                    "paper_authors": finding.paper_authors,
                    "paper_date": finding.paper_date.isoformat() if finding.paper_date else None,
                    "user_section": finding.user_section,
                    "user_claim": finding.user_claim,
                    "new_finding": finding.new_finding,
                    "explanation": finding.explanation,
                    "suggested_update": finding.suggested_update,
                }
            )

        citation_style = (payload.citation_style or "APA").strip() or "APA"
        heading = (payload.heading or "AI Revision Draft").strip() or "AI Revision Draft"
        ai_result = generate_ai_revision_draft(
            topic=profile.topic or project.name,
            citation_style=citation_style,
            source_text=source_doc.text,
            findings=findings_payload,
        )
        revised_draft = (ai_result.get("revised_draft") or "").strip()
        if not revised_draft:
            raise HTTPException(status_code=502, detail="AI returned an empty revised draft")

        references = ai_result.get("references") or []
        notes = ai_result.get("notes") or []
        generated_at = datetime.now(tz=timezone.utc).isoformat()

        references_block = "\n".join(f"- {ref}" for ref in references) if references else "- None"
        notes_block = "\n".join(f"- {note}" for note in notes) if notes else "- None"

        output = textwrap.dedent(
            f"""

            [{heading}]
            Generated at: {generated_at}
            Citation style: {citation_style}

            WARNING: AI-generated draft. Verify all claims and citations before use.

            {revised_draft}

            References ({citation_style}):
            {references_block}

            Evidence Notes:
            {notes_block}
            """
        )

        append_text_to_google_doc_tab(
            doc_id=profile.google_doc_id,
            tab_id=profile.ai_revision_tab_id,
            text=output,
            user_id=str(user.id),
        )

        return {
            "status": "ok",
            "ai_revision_tab_id": profile.ai_revision_tab_id,
            "ai_revision_tab_title": profile.ai_revision_tab_title,
            "citation_style": citation_style,
            "references_count": len(references),
            "notes_count": len(notes),
        }


@router.patch("/{project_id}/findings/{finding_id}")
def update_finding_status(
    project_id: str,
    finding_id: str,
    status: str,
    user: CurrentUser = Depends(get_current_user),
):
    allowed = {"pending", "resolved", "dismissed"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(allowed)}")
    with db_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.user_id == user.id).one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        finding = session.query(Finding).filter(Finding.id == finding_id, Finding.project_id == project.id).one_or_none()
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")
        finding.status = status
        return {"id": finding_id, "status": status}


@router.post("/{project_id}/link-google-doc")
def link_google_doc(project_id: str, payload: LinkGoogleDocRequest, user: CurrentUser = Depends(get_current_user)):
    settings = get_settings()
    doc_id = extract_google_doc_id(payload.google_doc_url)
    if not doc_id:
        raise HTTPException(status_code=400, detail="Invalid Google Doc URL")

    try:
        doc = download_google_doc_as_text(payload.google_doc_url, user_id=str(user.id))
        extracted = _normalize_extracted_profile(extract_research_profile(doc.text))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to read/analyze Google Doc: {e}") from e

    with db_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.user_id == user.id).one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        profile = session.query(ProjectProfile).filter(ProjectProfile.project_id == project.id).one_or_none()
        if not profile:
            profile = ProjectProfile(project_id=project.id)
            session.add(profile)
            session.flush()

        old_doc_id = profile.google_doc_id

        kb_uuid = profile.gradient_kb_id
        kb_warning: str | None = None
        try:
            if not kb_uuid:
                kb_uuid = create_knowledge_base(
                    name=f"project_{project.id}_literature",
                    description=f"Literature review for project {project.name}",
                )
                if settings.analysis_agent_uuid:
                    attach_kb_to_agent(agent_uuid=settings.analysis_agent_uuid, kb_uuid=kb_uuid)
                if settings.router_agent_uuid:
                    attach_kb_to_agent(agent_uuid=settings.router_agent_uuid, kb_uuid=kb_uuid)

            if kb_uuid:
                knowledge_base_add_text_source(kb_uuid=kb_uuid, filename="literature_review.txt", content=doc.text)
                knowledge_base_index(kb_uuid=kb_uuid)
        except Exception as e:
            kb_warning = str(e)

        profile.google_doc_url = payload.google_doc_url
        profile.google_doc_id = doc_id
        profile.review_last_updated = payload.review_last_updated
        profile.gradient_kb_id = kb_uuid
        profile.topic = extracted.get("topic")
        profile.keywords = extracted.get("keywords") or []
        profile.methodology = extracted.get("methodology")
        if old_doc_id and old_doc_id != doc_id:
            profile.ai_revision_tab_id = None
            profile.ai_revision_tab_title = None

        return {
            "status": "linked",
            "profile": extracted,
            "kb": {
                "enabled": bool(kb_uuid),
                "kb_id": kb_uuid,
                "warning": kb_warning,
            },
        }

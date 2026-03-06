from __future__ import annotations

from datetime import datetime, timezone
import re

from backend.db.models import Finding, MonitoringJob, Project, ProjectProfile, User
from backend.db.session import db_session
from backend.services.email_service import render_contradiction_email, send_email
from backend.services.google_docs import download_google_doc_as_text
from backend.services.google_docs import add_google_doc_comment, append_google_doc_ai_references
from backend.services.gradient_ai import extract_research_profile, run_router_monitoring
from backend.services.pubmed import search_pubmed


_DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)
_PMID_RE = re.compile(r"^\d{5,10}$")


def _citation_to_link(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return raw
    if raw.lower().startswith("http://") or raw.lower().startswith("https://"):
        return raw
    if _DOI_RE.match(raw):
        return f"https://doi.org/{raw}"
    if raw.lower().startswith("pmid:"):
        pmid = raw.split(":", 1)[1].strip()
        if _PMID_RE.match(pmid):
            return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    if _PMID_RE.match(raw):
        return f"https://pubmed.ncbi.nlm.nih.gov/{raw}/"
    return raw


def _build_weighted_pubmed_query(keywords: list[str]) -> str:
    cleaned = [kw.strip() for kw in (keywords or []) if kw and kw.strip()]
    if not cleaned:
        return ""

    high = cleaned[:4]
    medium = cleaned[4:8]
    low = cleaned[8:]

    terms: list[str] = []

    # High-priority terms: favor title/abstract and duplicate for weighting.
    for kw in high:
        term = f'"{kw}"[Title/Abstract]'
        terms.append(term)
        terms.append(term)

    # Medium-priority terms: title/abstract.
    for kw in medium:
        terms.append(f'"{kw}"[Title/Abstract]')

    # Lower-priority terms: all fields for broader recall.
    for kw in low:
        terms.append(f'"{kw}"[All Fields]')

    return "(" + " OR ".join(terms) + ")"


def _normalize_profile_fields(extracted: dict) -> dict:
    topic = extracted.get("topic")
    if topic is not None:
        topic = str(topic).strip() or None

    methodology = extracted.get("methodology")
    if methodology is not None:
        methodology = str(methodology).strip() or None
        methodology = methodology[:100]

    return {
        "topic": topic,
        "methodology": methodology,
    }


def _resync_project_profile(profile: ProjectProfile, user_id: str) -> str | None:
    """Re-downloads the linked Google Doc, refreshes profile fields, and returns the raw doc text."""
    if not profile.google_doc_url:
        return None

    doc = download_google_doc_as_text(profile.google_doc_url, user_id=user_id)
    extracted = _normalize_profile_fields(extract_research_profile(doc.text))

    profile.google_doc_id = doc.doc_id
    if extracted.get("topic"):
        profile.topic = extracted.get("topic")
    profile.methodology = extracted.get("methodology")
    profile.review_last_updated = datetime.now(tz=timezone.utc).date()
    return doc.text


def run_project_monitoring_job(*, job_id: str, project_id: str, date_after: str) -> None:
    with db_session() as session:
        job = session.query(MonitoringJob).filter(MonitoringJob.id == job_id).one()
        project = session.query(Project).filter(Project.id == project_id).one()
        user = session.query(User).filter(User.id == project.user_id).one()
        profile = session.query(ProjectProfile).filter(ProjectProfile.project_id == project.id).one_or_none()

        if not profile:
            job.status = "failed"
            job.error_message = "Missing project profile"
            job.completed_at = datetime.now(tz=timezone.utc)
            return
        if profile.monitoring_active is False:
            job.status = "completed"
            job.error_message = None
            job.completed_at = datetime.now(tz=timezone.utc)
            job.papers_found = 0
            job.contradictions_found = 0
            return
        if not profile.topic or not (profile.keywords or []):
            job.status = "failed"
            job.error_message = "Project missing topic/keywords (link a Google Doc first)"
            job.completed_at = datetime.now(tz=timezone.utc)
            return

        job.status = "running"
        job.started_at = datetime.now(tz=timezone.utc)
        session.flush()

        try:
            lit_review_text = _resync_project_profile(profile, user_id=str(user.id))
            session.flush()

            query = _build_weighted_pubmed_query(profile.keywords or [])
            if not query:
                raise RuntimeError("No valid keywords to build PubMed query")
            papers = search_pubmed(query=query, date_after=datetime.fromisoformat(date_after).date(), max_results=20)

            result = run_router_monitoring(
                user_id=str(user.id),
                topic=profile.topic,
                keywords=profile.keywords or [],
                date_after=date_after,
                kb_uuid=profile.gradient_kb_id or "",
                papers=papers,
                lit_review_text=lit_review_text,
            )
            findings = result.get("findings")
            if findings is None:
                findings = result.get("contradictions", [])
            findings = findings or []

            if profile.include_validation is False:
                filtered: list[dict] = []
                for entry in findings:
                    kind = (entry.get("finding_kind") or entry.get("contradiction_type") or "").strip().lower()
                    if kind == "confirmation":
                        continue
                    filtered.append(entry)
                findings = filtered

            ai_reference_links: list[str] = []

            for c in findings:
                paper_date = None
                paper_date_raw = c.get("paper_date")
                if isinstance(paper_date_raw, str) and paper_date_raw:
                    try:
                        paper_date = datetime.fromisoformat(paper_date_raw).date()
                    except Exception:
                        paper_date = None

                finding_kind = (c.get("finding_kind") or c.get("contradiction_type") or "contradiction").strip().lower()
                citations = c.get("citations") or []
                if not isinstance(citations, list):
                    citations = [str(citations)]
                citations = [str(x).strip() for x in citations if str(x).strip()]
                citation_links = [_citation_to_link(x) for x in citations]

                # Backfill citation links from DOI if model omitted citations.
                paper_doi = c.get("paper_doi")
                if not citation_links and paper_doi:
                    citation_links = [_citation_to_link(str(paper_doi))]

                for cite in citation_links:
                    if cite not in ai_reference_links:
                        ai_reference_links.append(cite)

                explanation = c.get("explanation") or ""
                if citation_links:
                    explanation = (
                        explanation
                        + "\n\nCitations:\n"
                        + "\n".join(f"- {cite}" for cite in citation_links)
                    ).strip()

                # Deduplication: skip if an identical finding already exists for this project.
                paper_doi_val = c.get("paper_doi")
                paper_title_val = c.get("paper_title") or "(untitled)"
                dup_query = session.query(Finding).filter(
                    Finding.project_id == project.id,
                    Finding.contradiction_type == finding_kind,
                )
                if paper_doi_val:
                    existing = dup_query.filter(Finding.paper_doi == paper_doi_val).first()
                else:
                    existing = dup_query.filter(Finding.paper_title == paper_title_val).first()
                if existing:
                    continue

                finding = Finding(
                    user_id=user.id,
                    project_id=project.id,
                    job_id=job.id,
                    paper_title=paper_title_val,
                    paper_doi=paper_doi_val,
                    paper_authors=c.get("paper_authors"),
                    paper_date=paper_date,
                    contradiction_type=finding_kind,
                    severity=c.get("severity"),
                    user_section=c.get("user_section"),
                    user_claim=c.get("user_claim"),
                    new_finding=c.get("new_finding"),
                    explanation=explanation,
                    suggested_update=c.get("suggested_update") or "",
                    status="pending",
                )
                session.add(finding)
                session.flush()

                should_comment = finding_kind in {"contradiction", "addition"}
                if finding_kind == "confirmation" and (profile.include_validation is not False):
                    should_comment = True

                if profile.google_doc_id and should_comment:
                    comment_lines = [
                        f"Finding Type: {finding_kind}",
                        f"Severity: {finding.severity or 'unspecified'}",
                    ]
                    # Citation line: authors + year + DOI
                    citation_parts = []
                    if finding.paper_authors:
                        citation_parts.append(finding.paper_authors)
                    if finding.paper_date:
                        citation_parts.append(str(finding.paper_date.year))
                    if finding.paper_doi:
                        citation_parts.append(f"doi:{finding.paper_doi}")
                    if citation_parts:
                        comment_lines += ["", "Source: " + " — ".join(citation_parts)]
                    comment_lines += [
                        "",
                        f"Suggestion:\n{finding.suggested_update}",
                        "",
                        f"Reasoning:\n{finding.explanation}",
                    ]
                    if finding.user_claim:
                        comment_lines.extend(["", f"Matched claim:\n{finding.user_claim}"])
                    if finding.new_finding:
                        comment_lines.extend(["", f"New evidence summary:\n{finding.new_finding}"])
                    add_google_doc_comment(
                        doc_id=profile.google_doc_id,
                        comment_text="\n".join(comment_lines).strip(),
                        location=c.get("location") or finding.user_section,
                        user_id=str(user.id),
                    )

            if profile.google_doc_id and ai_reference_links:
                append_google_doc_ai_references(
                    doc_id=profile.google_doc_id,
                    references=ai_reference_links[:40],
                    run_label=f"job {job.id}",
                    user_id=str(user.id),
                )

            now = datetime.now(tz=timezone.utc)
            job.status = "completed"
            job.completed_at = now
            papers_checked = int(result.get("papers_checked", 0) or 0)
            if papers_checked <= 0:
                papers_checked = len(papers)
            job.papers_found = papers_checked
            job.contradictions_found = len(findings)

            profile.last_checked_at = now

            if findings:
                send_email(
                    to=user.email,
                    subject=f"ConsensusTracker: New findings in {project.name}",
                    html_body=render_contradiction_email(findings),
                )

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(tz=timezone.utc)

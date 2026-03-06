"""
Quick diagnostic: shows the PubMed query built, papers returned, and AI response
for the most recently run job (or any project matching a name).

Usage:
  python debug_run.py
  python debug_run.py "Alzheimer"
"""
import sys
import json
from datetime import datetime, date, timezone, timedelta

from backend.db.session import db_session
from backend.db.models import Project, ProjectProfile, MonitoringJob
from backend.services.pubmed import search_pubmed
from backend.jobs.project_monitoring_runner import _build_weighted_pubmed_query
from backend.services.gradient_ai import run_router_monitoring
from backend.services.google_docs import download_google_doc_as_text

name_filter = sys.argv[1] if len(sys.argv) > 1 else None

with db_session() as session:
    q = session.query(Project)
    if name_filter:
        q = q.filter(Project.name.ilike(f"%{name_filter}%"))
    projects = q.all()

    if not projects:
        print("No matching projects found.")
        sys.exit(1)

    project = projects[0]
    print(f"\n=== Project: {project.name} (id={project.id}) ===")

    profile = session.query(ProjectProfile).filter(ProjectProfile.project_id == project.id).one_or_none()
    if not profile:
        print("No profile found — link a Google Doc first.")
        sys.exit(1)

    print(f"Topic       : {profile.topic}")
    print(f"Keywords    : {profile.keywords}")
    print(f"KB UUID     : {profile.gradient_kb_id}")
    print(f"Doc URL     : {profile.google_doc_url}")
    print(f"Last checked: {profile.last_checked_at}")

    # Show last job
    last_job = (
        session.query(MonitoringJob)
        .filter(MonitoringJob.project_id == project.id)
        .order_by(MonitoringJob.started_at.desc())
        .first()
    )
    if last_job:
        print(f"\nLast job    : status={last_job.status}  papers_found={last_job.papers_found}  findings={last_job.contradictions_found}")
        if last_job.error_message:
            print(f"  Error     : {last_job.error_message}")

    print("\n--- Building PubMed query ---")
    query = _build_weighted_pubmed_query(profile.keywords or [])
    print(f"Query: {query}")

    date_after_str = input("\nDate after (YYYY-MM-DD, default=1995-01-01): ").strip() or "1995-01-01"
    date_after = date.fromisoformat(date_after_str)

    print(f"\n--- Searching PubMed (max 20) ---")
    papers = search_pubmed(query=query, date_after=date_after, max_results=20)
    print(f"Papers returned: {len(papers)}")
    for p in papers:
        print(f"  [{p.get('year', '?')}] {p.get('title', '')[:80]}  (PMID:{p.get('pmid')})")

    if not papers:
        print("\n>>> PubMed returned 0 papers. The query may be too narrow or the date filter is too recent.")
        sys.exit(0)

    run_ai = input("\nRun AI analysis? (y/N): ").strip().lower() == "y"
    if not run_ai:
        sys.exit(0)

    # Download doc text for context injection (uses user's OAuth tokens if available)
    lit_review_text = None
    if profile.google_doc_url:
        print("\n--- Downloading Google Doc ---")
        try:
            doc = download_google_doc_as_text(profile.google_doc_url, user_id=str(project.user_id))
            lit_review_text = doc.text
            print(f"Doc text length: {len(lit_review_text)} chars")
        except Exception as e:
            print(f"Warning: could not download doc: {e}")

    print("\n--- Running router agent ---")
    result = run_router_monitoring(
        user_id=str(project.user_id),
        topic=profile.topic or "",
        keywords=profile.keywords or [],
        date_after=date_after_str,
        kb_uuid=profile.gradient_kb_id or "",
        papers=papers,
        lit_review_text=lit_review_text,
    )
    findings = result.get("findings") or []
    print(f"\nPapers checked: {result.get('papers_checked', '?')}")
    print(f"Findings returned: {len(findings)}")
    for f in findings:
        print(f"\n  [{f.get('finding_kind', '?').upper()}] {f.get('paper_title', '')[:70]}")
        print(f"  Severity : {f.get('severity')}")
        print(f"  Claim    : {f.get('user_claim', '')[:100]}")
        print(f"  Explain  : {f.get('explanation', '')[:150]}")

    print("\n--- Raw AI response ---")
    print(json.dumps(result, indent=2)[:3000])

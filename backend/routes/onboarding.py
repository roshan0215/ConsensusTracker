from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, HTTPException

from backend.db.models import ActivityLog, ResearchProfile, User
from backend.db.session import db_session
from backend.schemas.common import ExtractTopicRequest, OnboardRequest, OnboardResponse
from backend.services.google_docs import download_google_doc_as_text, extract_google_doc_id
from backend.services.gradient_ai import (
    attach_kb_to_agent,
    create_knowledge_base,
    extract_research_profile,
    knowledge_base_add_text_source,
    knowledge_base_index,
)
from backend.core.config import get_settings


router = APIRouter(prefix="/api", tags=["onboarding"])


@router.post("/extract-topic")
def extract_topic(payload: ExtractTopicRequest):
    doc = download_google_doc_as_text(payload.google_doc_url)
    profile = extract_research_profile(doc.text)
    profile["google_doc_id"] = doc.doc_id
    return profile


@router.post("/onboard", response_model=OnboardResponse)
def onboard(payload: OnboardRequest):
    settings = get_settings()
    google_doc_id = extract_google_doc_id(payload.google_doc_url)
    if not google_doc_id:
        raise HTTPException(status_code=400, detail="Invalid Google Doc URL")

    # Download doc first so we can fail fast on missing permissions.
    doc = download_google_doc_as_text(payload.google_doc_url)

    with db_session() as session:
        user = session.query(User).filter(User.email == payload.email).one_or_none()
        if user is None:
            user = User(email=str(payload.email))
            session.add(user)
            session.flush()

        user.google_doc_url = payload.google_doc_url
        user.google_doc_id = google_doc_id
        user.monitoring_active = True

        profile = session.query(ResearchProfile).filter(ResearchProfile.user_id == user.id).one_or_none()
        if profile is None:
            profile = ResearchProfile(user_id=user.id, topic=payload.profile.topic)
            session.add(profile)

        kb_uuid = profile.gradient_kb_id
        if not kb_uuid:
            kb_uuid = create_knowledge_base(
                name=f"user_literature_{user.id}",
                description=f"Literature review for {payload.profile.topic}",
            )
            if settings.analysis_agent_uuid:
                attach_kb_to_agent(agent_uuid=settings.analysis_agent_uuid, kb_uuid=kb_uuid)
            if settings.router_agent_uuid:
                attach_kb_to_agent(agent_uuid=settings.router_agent_uuid, kb_uuid=kb_uuid)

        knowledge_base_add_text_source(kb_uuid=kb_uuid, filename="literature_review.txt", content=doc.text)
        knowledge_base_index(kb_uuid=kb_uuid)

        profile.topic = payload.profile.topic
        profile.keywords = payload.profile.keywords
        profile.methodology = payload.profile.methodology
        profile.review_last_updated = payload.review_last_updated
        profile.gradient_kb_id = kb_uuid
        profile.updated_at = datetime.utcnow()

        session.add(ActivityLog(user_id=user.id, action="onboarded", details={"topic": profile.topic}))

        backfill_queued = False
        if payload.review_last_updated and (date.today() - payload.review_last_updated).days > 30:
            backfill_queued = True

        return OnboardResponse(
            status="success",
            user_id=str(user.id),
            backfill_queued=backfill_queued,
            profile=payload.profile,
        )


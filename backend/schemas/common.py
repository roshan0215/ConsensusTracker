from __future__ import annotations

from datetime import date
from pydantic import BaseModel, EmailStr, Field


class ExtractTopicRequest(BaseModel):
    google_doc_url: str = Field(..., min_length=8)


class ResearchProfilePayload(BaseModel):
    topic: str
    keywords: list[str] = []
    methodology: str | None = None
    key_questions: list[str] | None = None


class OnboardRequest(BaseModel):
    email: EmailStr
    google_doc_url: str
    review_last_updated: date | None = None
    profile: ResearchProfilePayload


class OnboardResponse(BaseModel):
    status: str
    user_id: str
    backfill_queued: bool
    profile: ResearchProfilePayload


class ManualJobRequest(BaseModel):
    user_id: str


class TriggerJobResponse(BaseModel):
    status: str
    job_id: str

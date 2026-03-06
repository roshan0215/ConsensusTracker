from __future__ import annotations

from datetime import date
from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class ProjectResponse(BaseModel):
    id: str
    name: str


class LinkGoogleDocRequest(BaseModel):
    google_doc_url: str
    review_last_updated: date | None = None


class EnsureAiRevisionTabRequest(BaseModel):
    title: str | None = Field(default="AI-Revision", min_length=1, max_length=200)


class GenerateAiRevisionRequest(BaseModel):
    citation_style: str | None = Field(default="APA", min_length=2, max_length=40)
    heading: str | None = Field(default="AI Revision Draft", min_length=3, max_length=120)

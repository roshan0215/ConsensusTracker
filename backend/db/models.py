from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    google_doc_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_doc_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    monitoring_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Google OAuth — set when user authorises via Google
    google_oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    google_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    research_profile: Mapped["ResearchProfile"] = relationship(back_populates="user", uselist=False)
    projects: Mapped[list["Project"]] = relationship(back_populates="user")
    jobs: Mapped[list["MonitoringJob"]] = relationship(back_populates="user")
    findings: Mapped[list["Finding"]] = relationship(back_populates="user")
    activity: Mapped[list["ActivityLog"]] = relationship(back_populates="user")


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_type: Mapped[str] = mapped_column(String(30), nullable=False)  # verify_email|magic_login
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="projects")
    profile: Mapped["ProjectProfile"] = relationship(back_populates="project", uselist=False)


class ProjectProfile(Base):
    __tablename__ = "project_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), unique=True)

    google_doc_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_doc_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    methodology: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_last_updated: Mapped[date | None] = mapped_column(Date, nullable=True)
    gradient_kb_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_revision_tab_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_revision_tab_title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    monitoring_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    include_validation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped[Project] = relationship(back_populates="profile")


class ResearchProfile(Base):
    __tablename__ = "research_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    topic: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    methodology: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_last_updated: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_coverage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    gradient_kb_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="research_profile")


class MonitoringJob(Base):
    __tablename__ = "monitoring_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)

    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # daily|backfill|manual
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    papers_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contradictions_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="jobs")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("monitoring_jobs.id"), nullable=True)

    paper_title: Mapped[str] = mapped_column(Text, nullable=False)
    paper_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paper_authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    paper_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    contradiction_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_claim: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_update: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="findings")


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="activity")

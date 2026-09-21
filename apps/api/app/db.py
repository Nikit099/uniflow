import uuid
from collections.abc import AsyncIterator
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    preferred_language: Mapped[str] = mapped_column(String(5), default="ru")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MaxIdentity(TimestampMixin, Base):
    __tablename__ = "max_identities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    max_user_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(10))
    last_authenticated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Membership(TimestampMixin, Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(30))


class StudentProfile(TimestampMixin, Base):
    __tablename__ = "student_profiles"
    __table_args__ = (UniqueConstraint("user_id", "organization_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    preferred_language: Mapped[str] = mapped_column(String(5), default="ru")
    citizenship: Mapped[str | None] = mapped_column(String(100))
    education_status: Mapped[str] = mapped_column(String(40), default="STUDENT")
    study_form: Mapped[str | None] = mapped_column(String(40))
    visa_requirement: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    residence_type: Mapped[str] = mapped_column(String(30), default="DORMITORY")
    arrival_date: Mapped[date | None] = mapped_column(Date)
    visa_expiration_date: Mapped[date | None] = mapped_column(Date)
    migration_registration_expiration_date: Mapped[date | None] = mapped_column(Date)
    tuition_type: Mapped[str | None] = mapped_column(String(40))
    previous_accommodation_type: Mapped[str | None] = mapped_column(String(40))
    profile_completion_status: Mapped[str] = mapped_column(String(30), default="INCOMPLETE")


class OfficialSource(TimestampMixin, Base):
    __tablename__ = "official_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    issuer: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(60), default="UNIVERSITY_GUIDANCE")
    url: Mapped[str] = mapped_column(String(1000))
    jurisdiction: Mapped[str] = mapped_column(String(255), default="Demo University")
    excerpt: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[str | None] = mapped_column(String(255))


class ProcedureTemplate(TimestampMixin, Base):
    __tablename__ = "procedure_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    code: Mapped[str] = mapped_column(String(100))
    title_i18n: Mapped[dict[str, str]] = mapped_column(JSON)
    description_i18n: Mapped[dict[str, str]] = mapped_column(JSON)


class ProcedureVersion(TimestampMixin, Base):
    __tablename__ = "procedure_versions"
    __table_args__ = (UniqueConstraint("procedure_template_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    procedure_template_id: Mapped[str] = mapped_column(
        ForeignKey("procedure_templates.id"), index=True
    )
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    applicability_rule: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ProcedureStep(TimestampMixin, Base):
    __tablename__ = "procedure_steps"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    procedure_version_id: Mapped[str] = mapped_column(
        ForeignKey("procedure_versions.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(100))
    title_i18n: Mapped[dict[str, str]] = mapped_column(JSON)
    sort_order: Mapped[int] = mapped_column(Integer)


class Requirement(TimestampMixin, Base):
    __tablename__ = "requirements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    procedure_version_id: Mapped[str] = mapped_column(
        ForeignKey("procedure_versions.id"), index=True
    )
    procedure_step_id: Mapped[str] = mapped_column(ForeignKey("procedure_steps.id"), index=True)
    code: Mapped[str] = mapped_column(String(100))
    title_i18n: Mapped[dict[str, str]] = mapped_column(JSON)
    description_i18n: Mapped[dict[str, str]] = mapped_column(JSON)
    requirement_type: Mapped[str] = mapped_column(String(50))
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    conditions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    student_action_i18n: Mapped[dict[str, str]] = mapped_column(JSON)
    staff_action_i18n: Mapped[dict[str, str]] = mapped_column(JSON)
    sort_order: Mapped[int] = mapped_column(Integer)


class Case(TimestampMixin, Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    student_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    procedure_version_id: Mapped[str] = mapped_column(
        ForeignKey("procedure_versions.id"), index=True
    )
    assigned_staff_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="IN_PROGRESS", index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="NORMAL")
    current_step_id: Mapped[str | None] = mapped_column(ForeignKey("procedure_steps.id"))
    source_mode: Mapped[str] = mapped_column(String(30), default="UNIVERSITY_CONFIG")
    version: Mapped[int] = mapped_column(Integer, default=1)
    requirements: Mapped[list["CaseRequirement"]] = relationship(
        back_populates="case", lazy="selectin"
    )


class CaseRequirement(TimestampMixin, Base):
    __tablename__ = "case_requirements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED")
    student_comment: Mapped[str | None] = mapped_column(Text)
    staff_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    case: Mapped[Case] = relationship(back_populates="requirements")
    requirement: Mapped[Requirement] = relationship(lazy="joined")
    documents: Mapped[list["Document"]] = relationship(lazy="selectin")


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    case_requirement_id: Mapped[str] = mapped_column(ForeignKey("case_requirements.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(100))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    issue_date: Mapped[date | None] = mapped_column(Date)
    expiration_date: Mapped[date | None] = mapped_column(Date)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class Comment(Base):
    __tablename__ = "case_comments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    author_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(20), default="STUDENT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(60))
    recipient_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class DemoNotification(Base):
    __tablename__ = "demo_notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(36))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    request_id: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class ProcessedWebhook(Base):
    __tablename__ = "processed_webhooks"
    update_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


settings = get_settings()
engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DemoLogin(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class MaxLogin(BaseModel):
    init_data: str


class UserView(BaseModel):
    id: str
    display_name: str
    email: str | None
    preferred_language: str
    role: str
    organization_id: str
    csrf_token: str


class ProfilePatch(BaseModel):
    preferred_language: str | None = None
    citizenship: str | None = None
    education_status: str | None = None
    study_form: str | None = None
    visa_requirement: str | None = None
    residence_type: str | None = None
    arrival_date: date | None = None
    visa_expiration_date: date | None = None
    tuition_type: str | None = None


class CaseCreate(BaseModel):
    procedure_version_id: str


class ReviewRequest(BaseModel):
    version: int
    reason: str = Field(min_length=3, max_length=2000)
    reason_code: str = "other"


class AcceptRequest(BaseModel):
    version: int


class ExternalEventRequest(BaseModel):
    note: str = Field(min_length=3, max_length=1000)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class ExplainRequest(BaseModel):
    case_requirement_id: str
    language: str = "ru"


class SourceInput(BaseModel):
    title: str
    issuer: str
    url: str
    excerpt: str
    status: str = "DRAFT"


class ProcedureImport(BaseModel):
    code: str
    title_i18n: dict[str, str]
    description_i18n: dict[str, str]
    applicability_rule: dict[str, Any]
    steps: list[dict[str, Any]]


class RequirementView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    version: int
    student_comment: str | None
    staff_comment: str | None
    requirement: dict[str, Any]
    documents: list[dict[str, Any]]


class CaseView(BaseModel):
    id: str
    status: str
    version: int
    procedure_version_id: str
    assigned_staff_user_id: str | None
    submitted_at: datetime | None
    verified_at: datetime | None
    due_at: datetime | None
    risk_level: str
    progress: int
    student_name: str | None = None
    procedure_title: dict[str, str] | None = None
    requirements: list[RequirementView] = []

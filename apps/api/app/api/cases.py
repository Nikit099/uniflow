from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import Actor, current_actor, mutation_roles
from app.core.config import Settings, get_settings
from app.db import (
    AuditLog,
    Case,
    CaseRequirement,
    Comment,
    Document,
    NotificationOutbox,
    ProcedureTemplate,
    ProcedureVersion,
    StudentProfile,
    User,
    get_db,
)
from app.integrations.storage import FileSystemStorage
from app.schemas import CaseCreate, CaseView, ProfilePatch, QuestionRequest, RequirementView
from app.services.cases import instantiate_requirements, load_case, submit_case

router = APIRouter(tags=["student cases"])


def valid_file_signature(content_type: str, data: bytes) -> bool:
    signatures = {
        "application/pdf": (b"%PDF-",),
        "image/jpeg": (b"\xff\xd8\xff",),
        "image/png": (b"\x89PNG\r\n\x1a\n",),
    }
    return any(data.startswith(signature) for signature in signatures.get(content_type, ()))


def requirement_view(item: CaseRequirement) -> RequirementView:
    req = item.requirement
    return RequirementView(
        id=item.id,
        status=item.status,
        version=item.version,
        student_comment=item.student_comment,
        staff_comment=item.staff_comment,
        requirement={
            "id": req.id,
            "code": req.code,
            "title_i18n": req.title_i18n,
            "description_i18n": req.description_i18n,
            "mandatory": req.mandatory,
            "source_ids": req.source_ids,
            "student_action_i18n": req.student_action_i18n,
        },
        documents=[
            {
                "id": doc.id,
                "original_filename": doc.original_filename,
                "mime_type": doc.mime_type,
                "uploaded_at": doc.uploaded_at.isoformat(),
            }
            for doc in item.documents
            if not doc.deleted_at
        ],
    )


async def case_view(db: AsyncSession, case: Case, include_requirements: bool = True) -> CaseView:
    items = case.requirements if include_requirements else []
    applicable = [item for item in case.requirements if item.status != "NOT_APPLICABLE"]
    finished = [item for item in applicable if item.status == "ACCEPTED"]
    version = await db.get(ProcedureVersion, case.procedure_version_id)
    template = await db.get(ProcedureTemplate, version.procedure_template_id) if version else None
    student = await db.get(User, case.student_user_id)
    return CaseView(
        id=case.id,
        status=case.status,
        version=case.version,
        procedure_version_id=case.procedure_version_id,
        assigned_staff_user_id=case.assigned_staff_user_id,
        submitted_at=case.submitted_at,
        verified_at=case.verified_at,
        due_at=case.due_at,
        risk_level=case.risk_level,
        progress=round(len(finished) / len(applicable) * 100) if applicable else 100,
        student_name=student.display_name if student else None,
        procedure_title=template.title_i18n if template else None,
        requirements=[requirement_view(item) for item in items],
    )


@router.get("/procedures")
async def procedures(
    actor: Actor = Depends(current_actor), db: AsyncSession = Depends(get_db)
) -> list[dict[str, object]]:
    rows = await db.execute(
        select(ProcedureVersion, ProcedureTemplate)
        .join(ProcedureTemplate)
        .where(
            ProcedureVersion.organization_id == actor.organization_id,
            ProcedureVersion.status == "ACTIVE",
        )
    )
    return [
        {
            "id": version.id,
            "version": version.version,
            "code": template.code,
            "title_i18n": template.title_i18n,
            "description_i18n": template.description_i18n,
        }
        for version, template in rows
    ]


@router.post("/cases", status_code=201)
async def create_case(
    body: CaseCreate,
    actor: Actor = Depends(mutation_roles("STUDENT")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    version = await db.scalar(
        select(ProcedureVersion).where(
            ProcedureVersion.id == body.procedure_version_id,
            ProcedureVersion.organization_id == actor.organization_id,
            ProcedureVersion.status == "ACTIVE",
        )
    )
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Procedure not found")
    existing = await db.scalar(
        select(Case).where(
            Case.student_user_id == actor.user.id,
            Case.procedure_version_id == version.id,
            Case.status.not_in(["COMPLETED", "CANCELLED"]),
        )
    )
    if existing:
        return {"id": existing.id}
    case = Case(
        organization_id=actor.organization_id,
        student_user_id=actor.user.id,
        procedure_version_id=version.id,
        status="IN_PROGRESS",
    )
    db.add(case)
    await db.flush()
    await instantiate_requirements(db, case)
    db.add(
        AuditLog(
            actor_user_id=actor.user.id,
            organization_id=actor.organization_id,
            action="CASE_CREATED",
            entity_type="case",
            entity_id=case.id,
        )
    )
    await db.commit()
    return {"id": case.id}


@router.get("/cases", response_model=list[CaseView])
async def list_cases(
    actor: Actor = Depends(current_actor), db: AsyncSession = Depends(get_db)
) -> list[CaseView]:
    query = (
        select(Case)
        .options(selectinload(Case.requirements))
        .where(Case.organization_id == actor.organization_id)
    )
    if actor.role == "STUDENT":
        query = query.where(Case.student_user_id == actor.user.id)
    cases = (await db.scalars(query.order_by(Case.updated_at.desc()))).all()
    return [await case_view(db, item, False) for item in cases]


@router.get("/cases/{case_id}", response_model=CaseView)
async def get_case(
    case_id: str, actor: Actor = Depends(current_actor), db: AsyncSession = Depends(get_db)
) -> CaseView:
    case = await load_case(db, case_id, actor.organization_id)
    if actor.role == "STUDENT" and case.student_user_id != actor.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return await case_view(db, case)


@router.patch("/cases/{case_id}/profile")
async def patch_profile(
    case_id: str,
    body: ProfilePatch,
    actor: Actor = Depends(mutation_roles("STUDENT")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    case = await load_case(db, case_id, actor.organization_id)
    if case.student_user_id != actor.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    profile = await db.scalar(
        select(StudentProfile).where(
            StudentProfile.user_id == actor.user.id,
            StudentProfile.organization_id == actor.organization_id,
        )
    )
    if not profile:
        profile = StudentProfile(user_id=actor.user.id, organization_id=actor.organization_id)
        db.add(profile)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    profile.profile_completion_status = "COMPLETE"
    await db.commit()
    return {"status": "updated"}


@router.post("/cases/{case_id}/documents", status_code=201)
async def upload_document(
    case_id: str,
    case_requirement_id: str = Form(),
    document_type: str = Form(),
    file: UploadFile = File(),
    actor: Actor = Depends(mutation_roles("STUDENT")),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    allowed = {"application/pdf", "image/jpeg", "image/png"}
    if file.content_type not in allowed:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF, JPG and PNG are allowed"
        )
    data = await file.read(settings.file_max_size_mb * 1024 * 1024 + 1)
    if len(data) > settings.file_max_size_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is too large")
    if not valid_file_signature(file.content_type, data):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "File content does not match MIME type",
        )
    case = await load_case(db, case_id, actor.organization_id)
    if case.student_user_id != actor.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    item = await db.scalar(
        select(CaseRequirement).where(
            CaseRequirement.id == case_requirement_id, CaseRequirement.case_id == case.id
        )
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requirement not found")
    storage = FileSystemStorage(settings.file_storage_path)
    key, digest = storage.save(data)
    doc = Document(
        owner_user_id=actor.user.id,
        case_id=case.id,
        case_requirement_id=item.id,
        document_type=document_type,
        original_filename=Path(file.filename or "document").name[:255],
        storage_key=key,
        mime_type=file.content_type,
        size_bytes=len(data),
        sha256=digest,
    )
    db.add(doc)
    await db.flush()
    item.status = "SUBMITTED"
    item.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.user.id,
            organization_id=actor.organization_id,
            action="DOCUMENT_UPLOADED",
            entity_type="document",
            entity_id=doc.id,
        )
    )
    await db.commit()
    return {"id": doc.id}


@router.get("/documents/{document_id}")
async def download_document(
    document_id: str,
    actor: Actor = Depends(current_actor),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    doc = await db.scalar(
        select(Document)
        .join(Case)
        .where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
            Case.organization_id == actor.organization_id,
        )
    )
    if not doc or (actor.role == "STUDENT" and doc.owner_user_id != actor.user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    data = FileSystemStorage(settings.file_storage_path).read(doc.storage_key)
    return StreamingResponse(
        iter([data]),
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="document-{doc.id}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    actor: Actor = Depends(mutation_roles("STUDENT")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    doc = await db.scalar(
        select(Document)
        .join(Case)
        .where(
            Document.id == document_id,
            Document.owner_user_id == actor.user.id,
            Case.organization_id == actor.organization_id,
            Document.deleted_at.is_(None),
        )
    )
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    doc.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return Response(status_code=204)


@router.post("/cases/{case_id}/submit")
async def submit(
    case_id: str,
    actor: Actor = Depends(mutation_roles("STUDENT")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    case = await load_case(db, case_id, actor.organization_id)
    if case.student_user_id != actor.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    await submit_case(db, case)
    await db.commit()
    return {"status": case.status}


@router.post("/cases/{case_id}/questions", status_code=201)
async def ask_staff(
    case_id: str,
    body: QuestionRequest,
    actor: Actor = Depends(mutation_roles("STUDENT")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    case = await load_case(db, case_id, actor.organization_id)
    if case.student_user_id != actor.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    comment = Comment(
        case_id=case.id,
        author_user_id=actor.user.id,
        body=body.question,
        visibility="STUDENT",
    )
    db.add(comment)
    await db.flush()
    if case.assigned_staff_user_id:
        db.add(
            NotificationOutbox(
                event_type="STAFF_MESSAGE",
                recipient_user_id=case.assigned_staff_user_id,
                payload={"case_id": case.id, "comment_id": comment.id},
            )
        )
    await db.commit()
    return {"id": comment.id}

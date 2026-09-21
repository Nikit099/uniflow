from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import AuditLog, Case, CaseRequirement, NotificationOutbox, Requirement, StudentProfile
from app.domain.cases import CaseStatus, InvalidTransition, transition
from app.domain.rules import evaluate_rule


async def instantiate_requirements(db: AsyncSession, case: Case) -> None:
    profile = await db.scalar(
        select(StudentProfile).where(
            StudentProfile.user_id == case.student_user_id,
            StudentProfile.organization_id == case.organization_id,
        )
    )
    context = {
        "student": {
            "residence_type": profile.residence_type.lower() if profile else None,
            "education_status": profile.education_status.lower() if profile else None,
            "visa_requirement": profile.visa_requirement if profile else None,
        }
    }
    requirements = (
        await db.scalars(
            select(Requirement)
            .where(Requirement.procedure_version_id == case.procedure_version_id)
            .order_by(Requirement.sort_order)
        )
    ).all()
    for requirement in requirements:
        applicable = evaluate_rule(requirement.conditions, context)
        db.add(
            CaseRequirement(
                case_id=case.id,
                requirement_id=requirement.id,
                status="NOT_STARTED" if applicable else "NOT_APPLICABLE",
            )
        )


async def load_case(db: AsyncSession, case_id: str, organization_id: str) -> Case:
    case = await db.scalar(
        select(Case)
        .options(selectinload(Case.requirements))
        .where(Case.id == case_id, Case.organization_id == organization_id)
    )
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return case


def set_case_status(case: Case, target: CaseStatus) -> None:
    try:
        case.status = transition(CaseStatus(case.status), target).value
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    case.version += 1


async def submit_case(db: AsyncSession, case: Case) -> None:
    if case.status == CaseStatus.READY_FOR_REVIEW:
        return
    if case.status not in {CaseStatus.IN_PROGRESS, CaseStatus.CHANGES_REQUESTED}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Case cannot be submitted")
    pending = [
        item
        for item in case.requirements
        if item.requirement.mandatory
        and item.status not in {"SUBMITTED", "ACCEPTED", "NOT_APPLICABLE"}
    ]
    if pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mandatory requirements are incomplete")
    set_case_status(case, CaseStatus.READY_FOR_REVIEW)
    case.submitted_at = datetime.now(timezone.utc)
    staff_id = case.assigned_staff_user_id
    if staff_id:
        db.add(
            NotificationOutbox(
                event_type="CASE_SUBMITTED",
                recipient_user_id=staff_id,
                payload={"case_id": case.id},
            )
        )
    db.add(
        AuditLog(
            actor_user_id=case.student_user_id,
            organization_id=case.organization_id,
            action="CASE_SUBMITTED",
            entity_type="case",
            entity_id=case.id,
        )
    )


async def review_requirement(
    db: AsyncSession,
    case_requirement: CaseRequirement,
    actor_id: str,
    expected_version: int,
    target: str,
    reason: str | None = None,
) -> None:
    if case_requirement.version != expected_version:
        raise HTTPException(status.HTTP_409_CONFLICT, "Requirement was changed by another reviewer")
    case = case_requirement.case
    if case.status == CaseStatus.READY_FOR_REVIEW:
        set_case_status(case, CaseStatus.UNDER_REVIEW)
    if case.status not in {CaseStatus.UNDER_REVIEW, CaseStatus.CHANGES_REQUESTED}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Case is not under review")
    case_requirement.status = target
    case_requirement.staff_comment = reason
    case_requirement.reviewed_by = actor_id
    case_requirement.reviewed_at = datetime.now(timezone.utc)
    case_requirement.version += 1
    action = "REQUIREMENT_ACCEPTED" if target == "ACCEPTED" else "REQUIREMENT_CHANGES_REQUESTED"
    db.add(
        AuditLog(
            actor_user_id=actor_id,
            organization_id=case.organization_id,
            action=action,
            entity_type="case_requirement",
            entity_id=case_requirement.id,
        )
    )
    if target == "CHANGES_REQUESTED":
        if case.status == CaseStatus.UNDER_REVIEW:
            set_case_status(case, CaseStatus.CHANGES_REQUESTED)
        db.add(
            NotificationOutbox(
                event_type="CHANGES_REQUESTED",
                recipient_user_id=case.student_user_id,
                payload={"case_id": case.id, "requirement_id": case_requirement.id},
            )
        )

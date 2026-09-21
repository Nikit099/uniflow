from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.cases import case_view
from app.api.deps import Actor, mutation_roles, require_roles
from app.db import AuditLog, Case, CaseRequirement, NotificationOutbox, get_db
from app.domain.cases import CaseStatus
from app.schemas import AcceptRequest, ExternalEventRequest, ReviewRequest
from app.services.cases import load_case, review_requirement, set_case_status

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/cases")
async def queue(
    actor: Actor = Depends(require_roles("STAFF", "ORG_ADMIN")), db: AsyncSession = Depends(get_db)
) -> list[dict[str, object]]:
    cases = (
        await db.scalars(
            select(Case)
            .options(selectinload(Case.requirements))
            .where(Case.organization_id == actor.organization_id)
            .order_by(Case.submitted_at.desc().nullslast())
        )
    ).all()
    return [(await case_view(db, case, False)).model_dump(mode="json") for case in cases]


@router.get("/cases/{case_id}")
async def staff_case(
    case_id: str,
    actor: Actor = Depends(require_roles("STAFF", "ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return (await case_view(db, await load_case(db, case_id, actor.organization_id))).model_dump(
        mode="json"
    )


@router.post("/cases/{case_id}/assign")
async def assign(
    case_id: str,
    actor: Actor = Depends(mutation_roles("STAFF", "ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    case = await load_case(db, case_id, actor.organization_id)
    case.assigned_staff_user_id = actor.user.id
    db.add(
        AuditLog(
            actor_user_id=actor.user.id,
            organization_id=actor.organization_id,
            action="STAFF_ASSIGNED",
            entity_type="case",
            entity_id=case.id,
        )
    )
    await db.commit()
    return {"assigned_staff_user_id": actor.user.id}


async def _item(db: AsyncSession, item_id: str, organization_id: str) -> CaseRequirement:
    item = await db.scalar(
        select(CaseRequirement)
        .options(selectinload(CaseRequirement.case))
        .join(Case)
        .where(CaseRequirement.id == item_id, Case.organization_id == organization_id)
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requirement not found")
    return item


@router.post("/requirements/{item_id}/accept")
async def accept(
    item_id: str,
    body: AcceptRequest,
    actor: Actor = Depends(mutation_roles("STAFF", "ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    item = await _item(db, item_id, actor.organization_id)
    await review_requirement(db, item, actor.user.id, body.version, "ACCEPTED")
    await db.commit()
    return {"status": item.status, "version": item.version}


@router.post("/requirements/{item_id}/request-changes")
async def request_changes(
    item_id: str,
    body: ReviewRequest,
    actor: Actor = Depends(mutation_roles("STAFF", "ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    item = await _item(db, item_id, actor.organization_id)
    await review_requirement(
        db, item, actor.user.id, body.version, "CHANGES_REQUESTED", body.reason
    )
    await db.commit()
    return {"status": item.status, "version": item.version}


@router.post("/requirements/{item_id}/not-applicable")
async def not_applicable(
    item_id: str,
    body: ReviewRequest,
    actor: Actor = Depends(mutation_roles("STAFF", "ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    item = await _item(db, item_id, actor.organization_id)
    await review_requirement(db, item, actor.user.id, body.version, "NOT_APPLICABLE", body.reason)
    await db.commit()
    return {"status": item.status, "version": item.version}


@router.post("/cases/{case_id}/verify")
async def verify(
    case_id: str,
    actor: Actor = Depends(mutation_roles("STAFF", "ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    case = await load_case(db, case_id, actor.organization_id)
    if case.status not in {CaseStatus.UNDER_REVIEW, CaseStatus.READY_FOR_REVIEW}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Case is not ready for verification")
    invalid = [
        item
        for item in case.requirements
        if item.requirement.mandatory and item.status not in {"ACCEPTED", "NOT_APPLICABLE"}
    ]
    if invalid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "All mandatory requirements must be accepted"
        )
    if case.status == CaseStatus.READY_FOR_REVIEW:
        set_case_status(case, CaseStatus.UNDER_REVIEW)
    set_case_status(case, CaseStatus.VERIFIED_BY_UNIVERSITY)
    case.verified_at = datetime.now(timezone.utc)
    db.add(
        NotificationOutbox(
            event_type="CASE_VERIFIED",
            recipient_user_id=case.student_user_id,
            payload={"case_id": case.id},
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.user.id,
            organization_id=actor.organization_id,
            action="CASE_VERIFIED",
            entity_type="case",
            entity_id=case.id,
        )
    )
    await db.commit()
    return {"status": case.status}


@router.post("/cases/{case_id}/external-events")
async def external_event(
    case_id: str,
    body: ExternalEventRequest,
    actor: Actor = Depends(mutation_roles("STAFF", "ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    case = await load_case(db, case_id, actor.organization_id)
    set_case_status(case, CaseStatus.EXTERNAL_ACTION_RECORDED)
    db.add(
        AuditLog(
            actor_user_id=actor.user.id,
            organization_id=actor.organization_id,
            action="EXTERNAL_STATUS_RECORDED",
            entity_type="case",
            entity_id=case.id,
            metadata_json={"note": body.note, "origin": "STAFF_REPORTED"},
        )
    )
    await db.commit()
    return {"status": case.status}


@router.get("/summary")
async def summary(
    actor: Actor = Depends(require_roles("STAFF", "ORG_ADMIN")), db: AsyncSession = Depends(get_db)
) -> dict[str, int]:
    result = await db.execute(
        select(Case.status, func.count(Case.id))
        .where(Case.organization_id == actor.organization_id)
        .group_by(Case.status)
    )
    counts: dict[str, int] = {status_name: count for status_name, count in result.all()}
    return {
        "waiting": counts.get("READY_FOR_REVIEW", 0),
        "changes": counts.get("CHANGES_REQUESTED", 0),
        "verified": counts.get("VERIFIED_BY_UNIVERSITY", 0),
    }

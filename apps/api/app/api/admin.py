from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Actor, mutation_roles, require_roles
from app.db import (
    AuditLog,
    Case,
    DemoNotification,
    Membership,
    OfficialSource,
    ProcedureStep,
    ProcedureTemplate,
    ProcedureVersion,
    Requirement,
    get_db,
)
from app.domain.rules import InvalidRule, evaluate_rule
from app.schemas import ProcedureImport, SourceInput

router = APIRouter(prefix="/admin", tags=["organization admin"])


@router.get("/demo-notifications")
async def demo_notifications(
    actor: Actor = Depends(require_roles("ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    rows = (
        await db.scalars(
            select(DemoNotification)
            .join(Membership, Membership.user_id == DemoNotification.recipient_user_id)
            .where(Membership.organization_id == actor.organization_id)
            .order_by(DemoNotification.created_at.desc())
            .limit(50)
        )
    ).all()
    return [
        {
            "id": row.id,
            "event_type": row.event_type,
            "payload": row.payload,
            "created_at": row.created_at,
            "label": "Локальная имитация MAX",
        }
        for row in rows
    ]


@router.get("/sources")
async def sources(
    actor: Actor = Depends(require_roles("ORG_ADMIN")), db: AsyncSession = Depends(get_db)
) -> list[dict[str, object]]:
    rows = (
        await db.scalars(
            select(OfficialSource)
            .where(OfficialSource.organization_id == actor.organization_id)
            .order_by(OfficialSource.updated_at.desc())
        )
    ).all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "issuer": row.issuer,
            "url": row.url,
            "excerpt": row.excerpt,
            "status": row.status,
            "last_verified_at": row.last_verified_at,
        }
        for row in rows
    ]


@router.post("/sources", status_code=201)
async def create_source(
    body: SourceInput,
    actor: Actor = Depends(mutation_roles("ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    source = OfficialSource(
        organization_id=actor.organization_id,
        title=body.title,
        issuer=body.issuer,
        url=body.url,
        excerpt=body.excerpt,
        status=body.status,
        last_verified_at=datetime.now(timezone.utc) if body.status == "VERIFIED" else None,
        verified_by=actor.user.id if body.status == "VERIFIED" else None,
    )
    db.add(source)
    await db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.user.id,
            organization_id=actor.organization_id,
            action="SOURCE_UPDATED",
            entity_type="source",
            entity_id=source.id,
        )
    )
    await db.commit()
    return {"id": source.id}


@router.get("/procedures")
async def procedures(
    actor: Actor = Depends(require_roles("ORG_ADMIN")), db: AsyncSession = Depends(get_db)
) -> list[dict[str, object]]:
    rows = await db.execute(
        select(ProcedureTemplate, ProcedureVersion)
        .join(ProcedureVersion)
        .where(ProcedureTemplate.organization_id == actor.organization_id)
        .order_by(ProcedureTemplate.code, ProcedureVersion.version.desc())
    )
    return [
        {
            "template_id": template.id,
            "code": template.code,
            "title_i18n": template.title_i18n,
            "version_id": version.id,
            "version": version.version,
            "status": version.status,
        }
        for template, version in rows
    ]


@router.get("/procedures/{version_id}/export")
async def export_procedure(
    version_id: str,
    actor: Actor = Depends(require_roles("ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    version = await db.scalar(
        select(ProcedureVersion).where(
            ProcedureVersion.id == version_id,
            ProcedureVersion.organization_id == actor.organization_id,
        )
    )
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Procedure version not found")
    template = await db.get(ProcedureTemplate, version.procedure_template_id)
    assert template is not None
    steps = (
        await db.scalars(
            select(ProcedureStep)
            .where(ProcedureStep.procedure_version_id == version.id)
            .order_by(ProcedureStep.sort_order)
        )
    ).all()
    result_steps: list[dict[str, object]] = []
    for step in steps:
        requirements = (
            await db.scalars(
                select(Requirement)
                .where(Requirement.procedure_step_id == step.id)
                .order_by(Requirement.sort_order)
            )
        ).all()
        result_steps.append(
            {
                "code": step.code,
                "title_i18n": step.title_i18n,
                "requirements": [
                    {
                        "code": requirement.code,
                        "title_i18n": requirement.title_i18n,
                        "description_i18n": requirement.description_i18n,
                        "requirement_type": requirement.requirement_type,
                        "mandatory": requirement.mandatory,
                        "conditions": requirement.conditions,
                        "source_ids": requirement.source_ids,
                        "student_action_i18n": requirement.student_action_i18n,
                        "staff_action_i18n": requirement.staff_action_i18n,
                    }
                    for requirement in requirements
                ],
            }
        )
    return {
        "code": template.code,
        "title_i18n": template.title_i18n,
        "description_i18n": template.description_i18n,
        "applicability_rule": version.applicability_rule,
        "steps": result_steps,
    }


@router.post("/procedures/import", status_code=201)
async def import_procedure(
    body: ProcedureImport,
    actor: Actor = Depends(mutation_roles("ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        evaluate_rule(body.applicability_rule, {"student": {}})
    except InvalidRule as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    template = await db.scalar(
        select(ProcedureTemplate).where(
            ProcedureTemplate.organization_id == actor.organization_id,
            ProcedureTemplate.code == body.code,
        )
    )
    if not template:
        template = ProcedureTemplate(
            organization_id=actor.organization_id,
            code=body.code,
            title_i18n=body.title_i18n,
            description_i18n=body.description_i18n,
        )
        db.add(template)
        await db.flush()
    latest = (
        await db.scalar(
            select(func.max(ProcedureVersion.version)).where(
                ProcedureVersion.procedure_template_id == template.id
            )
        )
        or 0
    )
    version = ProcedureVersion(
        procedure_template_id=template.id,
        organization_id=actor.organization_id,
        version=latest + 1,
        status="DRAFT",
        applicability_rule=body.applicability_rule,
    )
    db.add(version)
    await db.flush()
    for index, step_data in enumerate(body.steps):
        step = ProcedureStep(
            procedure_version_id=version.id,
            code=step_data["code"],
            title_i18n=step_data["title_i18n"],
            sort_order=index,
        )
        db.add(step)
        await db.flush()
        for r_index, requirement in enumerate(step_data.get("requirements", [])):
            db.add(
                Requirement(
                    procedure_version_id=version.id,
                    procedure_step_id=step.id,
                    code=requirement["code"],
                    title_i18n=requirement["title_i18n"],
                    description_i18n=requirement["description_i18n"],
                    requirement_type=requirement.get("requirement_type", "DOCUMENT"),
                    mandatory=requirement.get("mandatory", True),
                    conditions=requirement.get("conditions", {}),
                    source_ids=requirement.get("source_ids", []),
                    student_action_i18n=requirement.get("student_action_i18n", {}),
                    staff_action_i18n=requirement.get("staff_action_i18n", {}),
                    sort_order=r_index,
                )
            )
    await db.commit()
    return {"template_id": template.id, "version_id": version.id}


@router.post("/procedures/{version_id}/activate")
async def activate(
    version_id: str,
    actor: Actor = Depends(mutation_roles("ORG_ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    version = await db.scalar(
        select(ProcedureVersion).where(
            ProcedureVersion.id == version_id,
            ProcedureVersion.organization_id == actor.organization_id,
        )
    )
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Procedure version not found")
    requirements = (
        await db.scalars(select(Requirement).where(Requirement.procedure_version_id == version.id))
    ).all()
    if not requirements or any(not item.source_ids for item in requirements):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Every requirement must reference a source"
        )
    await db.execute(
        update(ProcedureVersion)
        .where(
            ProcedureVersion.procedure_template_id == version.procedure_template_id,
            ProcedureVersion.status == "ACTIVE",
        )
        .values(status="ARCHIVED")
    )
    version.status = "ACTIVE"
    version.valid_from = datetime.now(timezone.utc).date()
    db.add(
        AuditLog(
            actor_user_id=actor.user.id,
            organization_id=actor.organization_id,
            action="PROCEDURE_VERSION_ACTIVATED",
            entity_type="procedure_version",
            entity_id=version.id,
        )
    )
    await db.commit()
    return {"status": version.status}


@router.get("/metrics")
async def metrics(
    actor: Actor = Depends(require_roles("ORG_ADMIN")), db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    result = await db.execute(
        select(Case.status, func.count(Case.id))
        .where(Case.organization_id == actor.organization_id)
        .group_by(Case.status)
    )
    counts: dict[str, int] = {status_name: count for status_name, count in result.all()}
    return {
        "cases_started": sum(counts.values()),
        "submitted": counts.get("READY_FOR_REVIEW", 0) + counts.get("UNDER_REVIEW", 0),
        "verified": counts.get("VERIFIED_BY_UNIVERSITY", 0),
        "changes_requested": counts.get("CHANGES_REQUESTED", 0),
        "origin": "SYNTHETIC_DEMO",
    }


@router.get("/ai-config")
async def ai_config(actor: Actor = Depends(require_roles("ORG_ADMIN"))) -> dict[str, object]:
    return {"enabled": False, "provider": None, "model": None, "secrets_exposed": False}

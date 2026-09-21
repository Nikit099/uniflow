from datetime import date, datetime, timedelta, timezone

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import (
    Case,
    CaseRequirement,
    Membership,
    OfficialSource,
    Organization,
    ProcedureStep,
    ProcedureTemplate,
    ProcedureVersion,
    Requirement,
    StudentProfile,
    User,
)

DEMO_PASSWORD = "demo-only-password"


async def seed_demo(db: AsyncSession) -> None:
    if await db.scalar(select(Organization).where(Organization.slug == "demo-university")):
        return
    organization = Organization(slug="demo-university", name="Demo University", demo=True)
    db.add(organization)
    await db.flush()
    users = {
        "student": User(
            email="student@demo.local",
            display_name="Алекс Ли",
            preferred_language="ru",
            password_hash=PasswordHasher().hash(DEMO_PASSWORD),
        ),
        "staff": User(
            email="staff@demo.local",
            display_name="Мария Соколова",
            preferred_language="ru",
            password_hash=PasswordHasher().hash(DEMO_PASSWORD),
        ),
        "admin": User(
            email="admin@demo.local",
            display_name="Ирина Волкова",
            preferred_language="ru",
            password_hash=PasswordHasher().hash(DEMO_PASSWORD),
        ),
    }
    db.add_all(users.values())
    await db.flush()
    db.add_all(
        [
            Membership(
                user_id=users["student"].id, organization_id=organization.id, role="STUDENT"
            ),
            Membership(user_id=users["staff"].id, organization_id=organization.id, role="STAFF"),
            Membership(
                user_id=users["admin"].id, organization_id=organization.id, role="ORG_ADMIN"
            ),
            StudentProfile(
                user_id=users["student"].id,
                organization_id=organization.id,
                preferred_language="ru",
                citizenship="Синтетические данные",
                education_status="STUDENT",
                study_form="FULL_TIME",
                visa_requirement="VISA_REQUIRED",
                residence_type="DORMITORY",
                arrival_date=date.today() - timedelta(days=2),
                profile_completion_status="COMPLETE",
            ),
        ]
    )
    source = OfficialSource(
        organization_id=organization.id,
        title="Demo University: памятка по первичному оформлению после заселения",
        issuer="Demo University — учебная конфигурация",
        source_type="UNIVERSITY_GUIDANCE",
        url="https://example.org/demo-university/migration-guide",
        jurisdiction="Demo University",
        excerpt="После прибытия и заселения в общежитие студент передает сотруднику копии документа, удостоверяющего личность, миграционной карты и подтверждения проживания. Данные являются синтетической конфигурацией для демонстрации.",
        status="VERIFIED",
        last_verified_at=datetime.now(timezone.utc),
        verified_by=users["admin"].id,
    )
    db.add(source)
    await db.flush()
    template = ProcedureTemplate(
        organization_id=organization.id,
        code="initial_migration_registration",
        title_i18n={
            "ru": "Первичный комплект после прибытия",
            "en": "Initial arrival document package",
        },
        description_i18n={
            "ru": "Подготовка комплекта для проверки университетом",
            "en": "Prepare a package for university review",
        },
    )
    db.add(template)
    await db.flush()
    version = ProcedureVersion(
        procedure_template_id=template.id,
        organization_id=organization.id,
        version=1,
        status="ACTIVE",
        valid_from=date.today(),
        applicability_rule={
            "all": [
                {"field": "student.residence_type", "op": "eq", "value": "dormitory"},
                {"field": "student.education_status", "op": "eq", "value": "student"},
            ]
        },
    )
    db.add(version)
    await db.flush()
    step = ProcedureStep(
        procedure_version_id=version.id,
        code="prepare",
        title_i18n={"ru": "Подготовьте документы", "en": "Prepare documents"},
        sort_order=1,
    )
    db.add(step)
    await db.flush()
    specs = [
        (
            "identity",
            "Документ, удостоверяющий личность",
            "Identity document",
            "Добавьте безопасную демонстрационную копию страницы с данными.",
            "Upload a safe demo copy of the details page.",
        ),
        (
            "migration_card",
            "Миграционная карта",
            "Migration card",
            "Добавьте читаемую демонстрационную копию обеих сторон.",
            "Upload a readable demo copy of both sides.",
        ),
        (
            "dormitory",
            "Подтверждение проживания",
            "Accommodation confirmation",
            "Добавьте подтверждение заселения в общежитие.",
            "Upload dormitory accommodation confirmation.",
        ),
    ]
    requirements: list[Requirement] = []
    for order, (code, ru, en, action_ru, action_en) in enumerate(specs, 1):
        requirement = Requirement(
            procedure_version_id=version.id,
            procedure_step_id=step.id,
            code=code,
            title_i18n={"ru": ru, "en": en},
            description_i18n={
                "ru": f"{ru} требуется в демонстрационной конфигурации университета.",
                "en": f"{en} is required by the demo university configuration.",
            },
            requirement_type="DOCUMENT",
            mandatory=True,
            conditions={},
            source_ids=[source.id],
            student_action_i18n={"ru": action_ru, "en": action_en},
            staff_action_i18n={
                "ru": "Проверьте читаемость и соответствие данных.",
                "en": "Check readability and consistency.",
            },
            sort_order=order,
        )
        db.add(requirement)
        requirements.append(requirement)
    await db.flush()
    case = Case(
        organization_id=organization.id,
        student_user_id=users["student"].id,
        procedure_version_id=version.id,
        assigned_staff_user_id=users["staff"].id,
        status="IN_PROGRESS",
        due_at=datetime.now(timezone.utc) + timedelta(days=5),
        source_mode="SYNTHETIC_DEMO",
    )
    db.add(case)
    await db.flush()
    db.add_all(
        [
            CaseRequirement(case_id=case.id, requirement_id=requirement.id, status="NOT_STARTED")
            for requirement in requirements
        ]
    )
    await db.commit()

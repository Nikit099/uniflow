from datetime import date, datetime, timedelta, timezone

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import (
    Case,
    CaseRequirement,
    DemoNotification,
    Document,
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
from app.integrations.storage import FileSystemStorage

DEMO_ACCOUNTS = {
    "student": ("student@demo.local", "student123", "Алекс Ли"),
    "staff": ("staff@demo.local", "staff123", "Мария Соколова"),
    "admin": ("admin@demo.local", "admin123", "Ирина Волкова"),
}
DEMO_ROLES = {"student": "STUDENT", "staff": "STAFF", "admin": "ORG_ADMIN"}


async def seed_demo(db: AsyncSession) -> None:
    existing_organization = await db.scalar(
        select(Organization).where(Organization.slug == "demo-university")
    )
    if existing_organization:
        hasher = PasswordHasher()
        users: dict[str, User] = {}
        for role, (email, password, display_name) in DEMO_ACCOUNTS.items():
            user = await db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(
                    email=email,
                    display_name=display_name,
                    preferred_language="ru",
                    password_hash=hasher.hash(password),
                )
                db.add(user)
                await db.flush()
            else:
                user.password_hash = hasher.hash(password)
            users[role] = user
            membership = await db.scalar(
                select(Membership).where(
                    Membership.user_id == user.id,
                    Membership.organization_id == existing_organization.id,
                )
            )
            if membership:
                membership.role = DEMO_ROLES[role]
            else:
                db.add(
                    Membership(
                        user_id=user.id,
                        organization_id=existing_organization.id,
                        role=DEMO_ROLES[role],
                    )
                )
        await _ensure_student_profile(db, users["student"], existing_organization.id)
        await db.flush()
        version = await db.scalar(
            select(ProcedureVersion)
            .join(ProcedureTemplate)
            .where(
                ProcedureTemplate.organization_id == existing_organization.id,
                ProcedureTemplate.code == "initial_migration_registration",
                ProcedureVersion.status == "ACTIVE",
            )
            .order_by(ProcedureVersion.version.desc())
        )
        if version:
            active_requirements = list(
                (
                    await db.scalars(
                        select(Requirement)
                        .where(Requirement.procedure_version_id == version.id)
                        .order_by(Requirement.sort_order)
                    )
                ).all()
            )
            students = await _ensure_additional_students(db, existing_organization.id)
            students["student"] = users["student"]
            cases = await _ensure_case_examples(
                db,
                existing_organization.id,
                users["staff"].id,
                version.id,
                active_requirements,
                students,
            )
            await _ensure_demo_notifications(db, users["admin"].id, cases)
        await db.commit()
        return
    organization = Organization(slug="demo-university", name="Demo University", demo=True)
    db.add(organization)
    await db.flush()
    hasher = PasswordHasher()
    users = {
        role: User(
            email=email,
            display_name=display_name,
            preferred_language="ru",
            password_hash=hasher.hash(password),
        )
        for role, (email, password, display_name) in DEMO_ACCOUNTS.items()
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
    students = await _ensure_additional_students(db, organization.id)
    students["student"] = users["student"]
    cases = await _ensure_case_examples(
        db,
        organization.id,
        users["staff"].id,
        version.id,
        requirements,
        students,
    )
    await _ensure_demo_notifications(db, users["admin"].id, cases)
    await db.commit()


def _profile(user_id: str, organization_id: str) -> StudentProfile:
    return StudentProfile(
        user_id=user_id,
        organization_id=organization_id,
        preferred_language="ru",
        citizenship="Синтетические данные",
        education_status="STUDENT",
        study_form="FULL_TIME",
        visa_requirement="VISA_REQUIRED",
        residence_type="DORMITORY",
        arrival_date=date.today() - timedelta(days=2),
        profile_completion_status="COMPLETE",
    )


async def _ensure_student_profile(
    db: AsyncSession, user: User, organization_id: str
) -> None:
    profile = await db.scalar(
        select(StudentProfile).where(
            StudentProfile.user_id == user.id,
            StudentProfile.organization_id == organization_id,
        )
    )
    if not profile:
        db.add(_profile(user.id, organization_id))


async def _ensure_additional_students(
    db: AsyncSession, organization_id: str
) -> dict[str, User]:
    records = {
        "mei": ("demo-mei@demo.local", "Мэй Чэнь"),
        "luca": ("demo-luca@demo.local", "Лука Росси"),
        "sara": ("demo-sara@demo.local", "Сара Иванова"),
        "nina": ("demo-nina@demo.local", "Нина Орлова"),
    }
    students: dict[str, User] = {}
    for key, (email, name) in records.items():
        user = await db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(email=email, display_name=name, preferred_language="ru")
            db.add(user)
            await db.flush()
        students[key] = user
        membership = await db.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == organization_id,
            )
        )
        if not membership:
            db.add(
                Membership(
                    user_id=user.id,
                    organization_id=organization_id,
                    role="STUDENT",
                )
            )
        await _ensure_student_profile(db, user, organization_id)
    await db.flush()
    return students


async def _ensure_case_examples(
    db: AsyncSession,
    organization_id: str,
    staff_user_id: str,
    version_id: str,
    requirements: list[Requirement],
    students: dict[str, User],
) -> dict[str, Case]:
    now = datetime.now(timezone.utc)
    storage = FileSystemStorage(get_settings().file_storage_path)
    requirement_by_id = {item.id: item for item in requirements}
    examples = [
        ("student", "IN_PROGRESS", 0),
        ("mei", "CHANGES_REQUESTED", 0),
        ("luca", "READY_FOR_REVIEW", 1),
        ("sara", "UNDER_REVIEW", 2),
        ("nina", "VERIFIED_BY_UNIVERSITY", 3),
    ]
    cases: dict[str, Case] = {}
    for student_key, case_status, age_days in examples:
        student = students[student_key]
        case = await db.scalar(
            select(Case).where(
                Case.organization_id == organization_id,
                Case.student_user_id == student.id,
                Case.procedure_version_id == version_id,
                Case.status == case_status,
            )
        )
        fixture_key = f"{student_key}_{case_status.lower()}"
        if not case:
            event_time = now - timedelta(days=age_days)
            terminal = case_status in {"COMPLETED", "CANCELLED"}
            verified = case_status in {
                "VERIFIED_BY_UNIVERSITY",
                "EXTERNAL_ACTION_RECORDED",
                "COMPLETED",
            }
            submitted = case_status not in {"IN_PROGRESS", "CANCELLED"}
            case = Case(
                organization_id=organization_id,
                student_user_id=student.id,
                procedure_version_id=version_id,
                assigned_staff_user_id=(
                    None if fixture_key == "mei_ready_for_review" else staff_user_id
                ),
                status=case_status,
                submitted_at=event_time if submitted else None,
                verified_at=event_time if verified else None,
                closed_at=event_time if terminal else None,
                due_at=None if terminal or verified else now + timedelta(days=max(1, 5 - age_days)),
                risk_level="ELEVATED" if case_status == "CHANGES_REQUESTED" else "NORMAL",
                source_mode="SYNTHETIC_DEMO",
                created_at=event_time,
                updated_at=event_time,
            )
            db.add(case)
            await db.flush()
            for index, requirement in enumerate(requirements):
                item_status = _example_requirement_status(case_status, index)
                changed = case_status == "CHANGES_REQUESTED" and item_status == "CHANGES_REQUESTED"
                reviewed = item_status == "ACCEPTED" or changed
                db.add(
                    CaseRequirement(
                        case_id=case.id,
                        requirement_id=requirement.id,
                        status=item_status,
                        staff_comment=(
                            "Загрузите читаемую копию документа."
                            if changed
                            else None
                        ),
                        reviewed_by=staff_user_id if reviewed else None,
                        reviewed_at=event_time if reviewed else None,
                        version=2 if reviewed else 1,
                    )
                )
        await db.flush()
        await _ensure_example_documents(
            db,
            storage,
            case,
            student.id,
            staff_user_id,
            requirement_by_id,
        )
        cases[fixture_key] = case
    await db.flush()
    return cases


async def _ensure_example_documents(
    db: AsyncSession,
    storage: FileSystemStorage,
    case: Case,
    owner_user_id: str,
    staff_user_id: str,
    requirements: dict[str, Requirement],
) -> None:
    items = list(
        (
            await db.scalars(
                select(CaseRequirement).where(CaseRequirement.case_id == case.id)
            )
        ).all()
    )
    for item in items:
        if item.status not in {"SUBMITTED", "ACCEPTED"}:
            continue
        existing = await db.scalar(
            select(Document).where(
                Document.case_requirement_id == item.id,
                Document.deleted_at.is_(None),
            )
        )
        if existing:
            continue
        requirement = requirements.get(item.requirement_id)
        if not requirement:
            continue
        code = requirement.code.upper()
        content = _demo_pdf(f"SYNTHETIC DEMO DOCUMENT - {code}")
        storage_key, digest = storage.save(content)
        db.add(
            Document(
                owner_user_id=owner_user_id,
                case_id=case.id,
                case_requirement_id=item.id,
                document_type=requirement.code,
                original_filename=f"demo_{requirement.code}.pdf",
                storage_key=storage_key,
                mime_type="application/pdf",
                size_bytes=len(content),
                sha256=digest,
                metadata_json={"demo": True},
            )
        )


def _demo_pdf(label: str) -> bytes:
    stream = f"BT /F1 16 Tf 72 720 Td ({label}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n% synthetic demo\n")
    offsets = [0]
    for index, content in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(content)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(pdf)


def _example_requirement_status(case_status: str, index: int) -> str:
    if case_status in {"IN_PROGRESS", "CANCELLED"}:
        return "NOT_STARTED"
    if case_status in {"VERIFIED_BY_UNIVERSITY", "EXTERNAL_ACTION_RECORDED", "COMPLETED"}:
        return "ACCEPTED"
    if case_status == "UNDER_REVIEW" and index == 0:
        return "ACCEPTED"
    if case_status == "CHANGES_REQUESTED":
        if index == 0:
            return "ACCEPTED"
        return "CHANGES_REQUESTED" if index == 1 else "SUBMITTED"
    return "SUBMITTED"


async def _ensure_demo_notifications(
    db: AsyncSession, admin_user_id: str, cases: dict[str, Case]
) -> None:
    events = [
        ("CASE_SUBMITTED", "luca_ready_for_review"),
        ("CHANGES_REQUESTED", "mei_changes_requested"),
        ("CASE_VERIFIED", "nina_verified_by_university"),
    ]
    existing = list(
        (
            await db.scalars(
                select(DemoNotification).where(
                    DemoNotification.recipient_user_id == admin_user_id
                )
            )
        ).all()
    )
    known_fixtures = {item.payload.get("demo_fixture") for item in existing}
    for event_type, case_key in events:
        case = cases.get(case_key)
        if not case:
            continue
        fixture_key = f"notification_{case_key}"
        if fixture_key in known_fixtures:
            continue
        db.add(
            DemoNotification(
                recipient_user_id=admin_user_id,
                event_type=event_type,
                payload={"case_id": case.id, "demo_fixture": fixture_key},
                created_at=case.submitted_at or datetime.now(timezone.utc),
            )
        )

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.cases import valid_file_signature
from app.db import Base, Case, CaseRequirement
from app.services.cases import load_case, review_requirement


def test_upload_magic_bytes_must_match_content_type() -> None:
    assert valid_file_signature("application/pdf", b"%PDF-1.4\n")
    assert valid_file_signature("image/png", b"\x89PNG\r\n\x1a\nrest")
    assert not valid_file_signature("application/pdf", b"<script>alert(1)</script>")
    assert not valid_file_signature("image/svg+xml", b"<svg/>")


@pytest.mark.asyncio
async def test_stale_review_is_rejected() -> None:
    item = CaseRequirement(
        case_id="case",
        requirement_id="requirement",
        status="SUBMITTED",
        version=2,
    )
    with pytest.raises(HTTPException) as error:
        await review_requirement(MagicMock(), item, "staff", 1, "ACCEPTED")  # type: ignore[arg-type]
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_case_from_another_tenant_is_invisible() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        case = Case(
            organization_id="organization-a",
            student_user_id="student",
            procedure_version_id="procedure",
        )
        db.add(case)
        await db.commit()
        with pytest.raises(HTTPException) as error:
            await load_case(db, case.id, "organization-b")
        assert error.value.status_code == 404
    await engine.dispose()

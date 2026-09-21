from datetime import date

import pytest

from app.domain.cases import CaseStatus, InvalidTransition, transition
from app.domain.deadlines import DeadlineConfidence, calculate_deadline
from app.domain.rules import InvalidRule, evaluate_rule
from app.integrations.llm import parse_grounded_answer


def test_declarative_rule_engine() -> None:
    context = {"student": {"residence_type": "dormitory", "age": 21}}
    rule = {
        "all": [
            {"field": "student.residence_type", "op": "eq", "value": "dormitory"},
            {"field": "student.age", "op": "gte", "value": 18},
        ]
    }
    assert evaluate_rule(rule, context)
    assert not evaluate_rule({"field": "student.age", "op": "lt", "value": 18}, context)


def test_rule_engine_rejects_code_like_rule() -> None:
    with pytest.raises(InvalidRule):
        evaluate_rule({"eval": "__import__('os')"}, {})


def test_case_state_machine_blocks_skips() -> None:
    assert (
        transition(CaseStatus.IN_PROGRESS, CaseStatus.READY_FOR_REVIEW)
        == CaseStatus.READY_FOR_REVIEW
    )
    with pytest.raises(InvalidTransition):
        transition(CaseStatus.DRAFT, CaseStatus.UNDER_REVIEW)


def test_deadline_marks_unverified_working_calendar() -> None:
    result = calculate_deadline(date(2026, 9, 21), 3, "WORKING_DAYS", "AFTER_EVENT")
    assert result.value is None
    assert result.confidence == DeadlineConfidence.REQUIRES_CONFIRMATION


def test_llm_output_must_reference_allowed_sources() -> None:
    valid = parse_grounded_answer(
        {
            "answer": "Grounded",
            "source_ids": ["source-1"],
            "uncertainty": "LOW",
            "needs_human": False,
        },
        {"source-1"},
    )
    assert valid.answer == "Grounded"
    with pytest.raises(ValueError):
        parse_grounded_answer(
            {
                "answer": "Invented",
                "source_ids": ["other"],
                "uncertainty": "LOW",
                "needs_human": False,
            },
            {"source-1"},
        )

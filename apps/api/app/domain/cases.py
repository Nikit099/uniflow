from enum import StrEnum


class CaseStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    VERIFIED_BY_UNIVERSITY = "VERIFIED_BY_UNIVERSITY"
    EXTERNAL_ACTION_RECORDED = "EXTERNAL_ACTION_RECORDED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.DRAFT: {CaseStatus.IN_PROGRESS, CaseStatus.CANCELLED},
    CaseStatus.IN_PROGRESS: {CaseStatus.READY_FOR_REVIEW, CaseStatus.CANCELLED},
    CaseStatus.READY_FOR_REVIEW: {CaseStatus.UNDER_REVIEW, CaseStatus.CHANGES_REQUESTED},
    CaseStatus.UNDER_REVIEW: {CaseStatus.CHANGES_REQUESTED, CaseStatus.VERIFIED_BY_UNIVERSITY},
    CaseStatus.CHANGES_REQUESTED: {CaseStatus.READY_FOR_REVIEW, CaseStatus.CANCELLED},
    CaseStatus.VERIFIED_BY_UNIVERSITY: {CaseStatus.EXTERNAL_ACTION_RECORDED, CaseStatus.COMPLETED},
    CaseStatus.EXTERNAL_ACTION_RECORDED: {CaseStatus.COMPLETED},
    CaseStatus.COMPLETED: set(),
    CaseStatus.CANCELLED: set(),
}


class InvalidTransition(ValueError):
    pass


def transition(current: CaseStatus, target: CaseStatus) -> CaseStatus:
    if target not in TRANSITIONS[current]:
        raise InvalidTransition(f"Cannot transition from {current} to {target}")
    return target

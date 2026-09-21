from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class DeadlineConfidence(StrEnum):
    CALCULATED = "CALCULATED"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"


@dataclass(frozen=True)
class DeadlineResult:
    value: date | None
    confidence: DeadlineConfidence
    explanation: str


def calculate_deadline(
    event: date | None, amount: int, unit: str, direction: str
) -> DeadlineResult:
    if event is None:
        return DeadlineResult(
            None, DeadlineConfidence.REQUIRES_CONFIRMATION, "Event date is missing"
        )
    sign = -1 if direction == "BEFORE_EVENT" else 1
    if unit == "CALENDAR_DAYS":
        value = event + timedelta(days=sign * amount)
        return DeadlineResult(
            value, DeadlineConfidence.CALCULATED, f"{amount} calendar days from event"
        )
    return DeadlineResult(
        None, DeadlineConfidence.REQUIRES_CONFIRMATION, "Working-day calendar is not verified"
    )

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StepResult:
    step: str
    status: str  # success | error | skipped
    duration_ms: int
    output: Any | None = None
    detail: str | None = None

from dataclasses import dataclass, field
from typing import Any

from domain.value_objects import ScreenRegion


@dataclass(frozen=True)
class WorkflowStep:
    action: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScreenSpec:
    id: str
    anchors: list[str]
    regions: dict[str, ScreenRegion] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowSpec:
    """Representa o contrato YAML de um workflow, imutavel apos o parse."""

    id: str
    timeout: int
    retries: int
    variables: dict[str, Any]
    steps: list[WorkflowStep]

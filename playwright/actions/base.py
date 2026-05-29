"""Base para todas as actions. Recebe a sessão do browser por injeção."""

from abc import ABC, abstractmethod
from typing import Any

from application.ports import AbstractBrowserSession
from domain.services import StateMachine


class BaseAction(ABC):
    def __init__(
        self,
        session: AbstractBrowserSession,
        state_machine: StateMachine | None = None,
        screen_handler_registry: dict | None = None,
    ):
        self.session = session
        self.sm = state_machine
        # Registro de AbstractScreenHandler por screen_id.
        # Injetado pelo WorkflowRunnerUseCase quando há handlers registrados.
        self.screen_handlers: dict = screen_handler_registry or {}

    @abstractmethod
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> Any:
        """Executa a action e retorna um output (pode ser None)."""
        ...

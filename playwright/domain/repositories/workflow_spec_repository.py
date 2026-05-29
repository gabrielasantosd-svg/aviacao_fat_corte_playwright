from abc import ABC, abstractmethod

from domain.entities import ScreenSpec, WorkflowSpec


class AbstractWorkflowSpecRepository(ABC):
    @abstractmethod
    def get_workflow(self, workflow_id: str) -> WorkflowSpec: ...

    @abstractmethod
    def get_screen(self, screen_id: str) -> ScreenSpec: ...

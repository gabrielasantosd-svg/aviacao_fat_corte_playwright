from typing import Any

from actions.base import BaseAction
from infrastructure.vision import ScreenshotService


class AssertTextAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> None:
        text = params.get("value", "")
        found = self.session.find_text(text)
        if not found:
            raise AssertionError(f"Texto '{text}' não encontrado na tela.")


class ScreenshotAction(BaseAction):
    def __init__(self, session, state_machine=None, screen_handler_registry=None, job_id: str = ""):
        super().__init__(session, state_machine, screen_handler_registry)
        self._job_id = job_id
        self._svc = ScreenshotService()

    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> str:
        label = params.get("label", "step")
        raw = self.session.screenshot()
        path = self._svc.save(raw, job_id=self._job_id or "job", label=label)
        return path


class WaitTextAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> None:
        text = params.get("value", "")
        timeout = int(params.get("timeout_ms", 20_000))
        self.session.wait_for_text_visible(text, timeout_ms=timeout)


class ExtractRegionAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> str:
        selector = params.get("selector", "")
        if not selector:
            return ""
        return self.session.wait_and_extract_text(selector)


class FinishAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> None:
        return None  # sinaliza fim do workflow

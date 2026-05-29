from typing import Any

from actions.base import BaseAction


class ClickTextAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> None:
        text = params.get("value", "")
        self.session.click_text(text)

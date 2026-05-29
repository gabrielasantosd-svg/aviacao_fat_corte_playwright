from typing import Any

from actions.base import BaseAction


class TypeAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> None:
        value = params.get("value", "")
        selector = params.get("selector", ":focus")
        self.session.type_text(selector, value)


class KeyAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> None:
        key = params.get("value", "")
        self.session.press_key(key)


class ShortcutAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> None:
        key = params.get("value", "")
        self.session.press_key(key)

"""
Registry central de actions.
Mapeia o id da action (usado no YAML) para sua classe.
"""

from actions.click_text import ClickTextAction
from actions.keyboard import KeyAction, ShortcutAction, TypeAction
from actions.login import LoginAction
from actions.misc import (
    AssertTextAction,
    ExtractRegionAction,
    FinishAction,
    ScreenshotAction,
    WaitTextAction,
)
from actions.search_routine import SearchRoutineAction
from actions.wait_screen import WaitScreenAction

ACTION_REGISTRY: dict = {
    "login": LoginAction,
    "search_routine": SearchRoutineAction,
    "wait_screen": WaitScreenAction,
    "click_text": ClickTextAction,
    "type": TypeAction,
    "key": KeyAction,
    "shortcut": ShortcutAction,
    "assert_text": AssertTextAction,
    "screenshot": ScreenshotAction,
    "wait_text": WaitTextAction,
    "extract_region": ExtractRegionAction,
    "finish": FinishAction,
}

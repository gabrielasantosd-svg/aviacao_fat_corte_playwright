import importlib
from typing import Any

from infrastructure.browser import PlaywrightSession
from infrastructure.persistence import SQLiteJobRepository
from infrastructure.specs import YamlWorkflowSpecRepository

CeleryJobDispatcher: Any
try:
    CeleryJobDispatcher = importlib.import_module("infrastructure.messaging").CeleryJobDispatcher
except ModuleNotFoundError:
    CeleryJobDispatcher = None

OCREngine: Any
ScreenshotService: Any
try:
    vision_module = importlib.import_module("infrastructure.vision")
    OCREngine = vision_module.OCREngine
    ScreenshotService = vision_module.ScreenshotService
except ModuleNotFoundError:
    ScreenshotService = None
    OCREngine = None

__all__ = [
    "CeleryJobDispatcher",
    "OCREngine",
    "PlaywrightSession",
    "SQLiteJobRepository",
    "ScreenshotService",
    "YamlWorkflowSpecRepository",
]

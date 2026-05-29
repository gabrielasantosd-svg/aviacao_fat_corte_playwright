"""
YamlWorkflowSpecRepository — lê specs de workflows e screens de arquivos YAML.
Implementa a interface do domínio sem vazar paths para o domínio.
"""

import os

import yaml

from domain.entities import ScreenSpec, WorkflowSpec, WorkflowStep
from domain.repositories import AbstractWorkflowSpecRepository
from domain.value_objects import ScreenRegion
from settings import settings


class YamlWorkflowSpecRepository(AbstractWorkflowSpecRepository):
    def __init__(self, specs_dir: str = settings.SPECS_DIR):
        self._specs_dir = specs_dir

    def get_workflow(self, workflow_id: str) -> WorkflowSpec:
        path = os.path.join(self._specs_dir, "workflows", f"{workflow_id}.yaml")
        data = self._load(path)
        wf = data["workflow"]
        rt = data.get("runtime", {})
        raw_steps = data.get("steps", [])

        steps = [
            WorkflowStep(
                action=s["action"],
                params={k: v for k, v in s.items() if k != "action"},
            )
            for s in raw_steps
        ]

        return WorkflowSpec(
            id=wf["id"],
            timeout=rt.get("timeout", 300),
            retries=rt.get("retries", 3),
            variables=data.get("variables", {}),
            steps=steps,
        )

    def get_screen(self, screen_id: str) -> ScreenSpec:
        path = os.path.join(self._specs_dir, "screens", f"{screen_id}.yaml")
        data = self._load(path)
        sc = data["screen"]

        anchors = [a["text"] for a in data.get("anchors", [])]

        regions = {}
        for name, coords in data.get("regions", {}).items():
            regions[name] = ScreenRegion(
                name=name,
                x=coords["x"],
                y=coords["y"],
                width=coords["width"],
                height=coords["height"],
            )

        return ScreenSpec(id=sc["id"], anchors=anchors, regions=regions)

    # ── private ───────────────────────────────────────────────────────

    @staticmethod
    def _load(path: str) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Spec não encontrada: {path}")
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

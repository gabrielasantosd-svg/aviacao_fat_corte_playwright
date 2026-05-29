"""
WorkflowExecutionService — domain service puro.
Orquestra a execução de steps sem conhecer infra (browser, OCR, DB).
Depende de ports (abstrações) injetadas pela camada de aplicação.
"""

import logging
import time
from typing import Any

from domain.entities import Job, WorkflowSpec, WorkflowStep
from domain.services.state_machine import StateMachine
from domain.value_objects import StepResult

log = logging.getLogger(__name__)


class WorkflowExecutionService:
    def __init__(self, action_registry: dict, state_machine: StateMachine):
        self._actions = action_registry
        self._sm = state_machine

    def execute(self, job: Job, spec: WorkflowSpec) -> dict[str, Any]:
        """
        Executa cada step do workflow em ordem determinística.
        Retorna um dicionário com os outputs coletados.
        """
        outputs: dict[str, Any] = {}
        merged_vars = {**spec.variables, **job.variables}
        total_steps = len(spec.steps)
        log.info(
            "[workflow] Iniciando workflow '%s' — %d step(s)",
            spec.id if hasattr(spec, "id") else "?",
            total_steps,
        )

        for idx, raw_step in enumerate(spec.steps, start=1):
            step = self._resolve_variables(raw_step, merged_vars)
            log.info(
                "[workflow] Step %d/%d — ação='%s' params=%s",
                idx,
                total_steps,
                step.action,
                step.params,
            )
            result = self._execute_step(job, step, outputs)
            job.add_step(result)

            if result.status == "error":
                log.error(
                    "[workflow] Step '%s' FALHOU (%dms): %s",
                    step.action,
                    result.duration_ms,
                    result.detail,
                )
                raise RuntimeError(f"Step '{step.action}' falhou: {result.detail}")

            log.info("[workflow] Step '%s' concluído em %dms", step.action, result.duration_ms)

            if result.output is not None:
                outputs[step.action] = result.output

            if step.action == "finish":
                log.info("[workflow] Step 'finish' encontrado — encerrando")
                break

        log.info("[workflow] Workflow finalizado. Outputs: %s", list(outputs.keys()))
        return outputs

    # ── private ───────────────────────────────────────────────────────

    def _execute_step(self, job: Job, step: WorkflowStep, context: dict) -> StepResult:
        action_entry = self._actions.get(step.action)
        if action_entry is None:
            return StepResult(
                step=step.action,
                status="error",
                duration_ms=0,
                detail=f"Ação '{step.action}' não registrada.",
            )

        t0 = time.monotonic()
        try:
            action = self._build_action(action_entry)
            output = action.execute(step.params, context)
            duration = int((time.monotonic() - t0) * 1000)
            return StepResult(
                step=step.action,
                status="success",
                duration_ms=duration,
                output=output,
            )
        except Exception as exc:
            duration = int((time.monotonic() - t0) * 1000)
            log.exception("[workflow] Exceção em '%s' após %dms", step.action, duration)
            return StepResult(
                step=step.action,
                status="error",
                duration_ms=duration,
                detail=str(exc),
            )

    def _build_action(self, action_entry):
        # actions já são instâncias criadas pelo WorkflowRunnerUseCase
        # (com session, state_machine e screen_handlers injetados)
        if hasattr(action_entry, "execute"):
            return action_entry

        # fallback: action_entry ainda é uma classe (uso legado)
        return action_entry(self._sm)

    @staticmethod
    def _resolve_variables(step: WorkflowStep, variables: dict) -> WorkflowStep:
        """Substitui placeholders {var} nos params do step."""
        resolved = {}
        for k, v in step.params.items():
            if isinstance(v, str):
                for var_name, var_value in variables.items():
                    v = v.replace(f"{{{var_name}}}", str(var_value or ""))
            resolved[k] = v
        return WorkflowStep(action=step.action, params=resolved)

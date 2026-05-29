"""WorkflowRunnerUseCase orquestra a execucao de um workflow em um worker.

Recebe implementacoes concretas de infraestrutura via injecao de dependencia.
"""

from typing import Any

from application.ports import AbstractBrowserSession
from domain.repositories import AbstractJobRepository, AbstractWorkflowSpecRepository
from domain.services import StateMachine, WorkflowExecutionService


class WorkflowRunnerUseCase:
    def __init__(
        self,
        job_repo: AbstractJobRepository,
        spec_repo: AbstractWorkflowSpecRepository,
        session: AbstractBrowserSession,
        action_registry: dict,
        screen_handler_registry: dict | None = None,
    ):
        self._job_repo = job_repo
        self._spec_repo = spec_repo
        self._session = session
        self._action_registry = action_registry
        self._screen_handlers = screen_handler_registry or {}

    def execute(self, job_id: str, workflow_id: str, variables: dict[str, Any]) -> dict:
        _ = variables
        job = self._job_repo.get(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' não encontrado.")

        spec = self._spec_repo.get_workflow(workflow_id)

        # Carrega as telas no state machine.
        sm = StateMachine()
        for step in spec.steps:
            screen_id = step.params.get("screen")
            if screen_id:
                try:
                    screen_spec = self._spec_repo.get_screen(screen_id)
                    sm.register(screen_spec)
                except Exception:
                    pass

        # Instancia as actions injetando sessao, state machine e screen handlers.
        enriched_registry = (
            {
                name: cls(self._session, sm, self._screen_handlers)
                for name, cls in self._action_registry.items()
            }
            if self._action_registry
            else {}
        )

        engine = WorkflowExecutionService(
            action_registry=enriched_registry,
            state_machine=sm,
        )

        job.start(worker_id="local")
        self._job_repo.save(job)

        try:
            result = engine.execute(job, spec)
            job.succeed(result)
        except Exception as exc:
            job.fail(str(exc))
            raise
        finally:
            self._job_repo.save(job)

        return result

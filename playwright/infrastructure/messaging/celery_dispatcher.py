from typing import Any

from application.ports import AbstractJobDispatcher
from workers.celery_app import celery_app


class CeleryJobDispatcher(AbstractJobDispatcher):
    def dispatch(self, job_id: str, workflow_id: str, variables: dict[str, Any]) -> None:
        celery_app.send_task(
            "workers.job_worker.run_workflow",
            kwargs={"job_id": job_id, "workflow_id": workflow_id, "variables": variables},
            task_id=job_id,
            queue="gsfat_jobs",
        )

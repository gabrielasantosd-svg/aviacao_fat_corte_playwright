from celery import Celery

from settings import settings

celery_app = Celery(
    "poc_gsfat",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["workers.job_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue="gsfat_jobs",
    worker_concurrency=1,  # 1 job por worker (isolamento visual)
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
)

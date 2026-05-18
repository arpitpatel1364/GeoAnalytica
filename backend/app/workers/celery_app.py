from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "geoanalytica",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.run_query_task": {"queue": "queries"},
        "app.workers.tasks.check_alerts_task": {"queue": "alerts"},
        "app.workers.tasks.run_scheduled_exports_task": {"queue": "exports"},
    },
    beat_schedule={
        "check-alerts-every-hour": {
            "task": "app.workers.tasks.check_alerts_task",
            "schedule": crontab(minute=0),  # Every hour
        },
        "run-scheduled-exports-daily": {
            "task": "app.workers.tasks.run_scheduled_exports_task",
            "schedule": crontab(hour=6, minute=0),  # 6 AM UTC daily
        },
    },
)

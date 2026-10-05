"""Celery application for background jobs and scheduled (Beat) tasks.

The worker and the Beat scheduler run as separate processes against the Redis
broker (see `.env` CELERY_BROKER_URL). Tasks execute inside a Flask app context
so they can use the database and the service layer.

Run locally (Redis from docker-compose must be up):

    celery -A app.celery_app.celery_app worker --loglevel=info
    celery -A app.celery_app.celery_app beat   --loglevel=info

The task LOGIC lives in the service layer (e.g. `sales.services.escalation
.nightly_scan`); tasks in `app/tasks.py` are thin wrappers, so everything is
unit-testable without a running worker.
"""

from __future__ import annotations

from typing import Any

from celery import Celery
from celery.schedules import crontab

from . import create_app
from .config import get_config


def _make_celery() -> Celery:
    cfg = get_config()
    celery = Celery(
        "white_moon",
        broker=cfg.CELERY_BROKER_URL,
        backend=cfg.CELERY_RESULT_BACKEND,
        include=["app.tasks"],
    )
    celery.conf.update(
        task_track_started=True,
        task_acks_late=True,
        worker_max_tasks_per_child=200,
        timezone="Africa/Cairo",
        enable_utc=False,
        beat_schedule={
            # Daily credit maintenance (docs/04 §1): recompute tiers + dunning.
            "nightly-credit-scan": {
                "task": "credit.nightly_scan",
                "schedule": crontab(hour="2", minute="0"),  # 02:00 Africa/Cairo
            },
            # Proactive reminders (docs/04 §2): dues coming due in a few days.
            "daily-due-reminders": {
                "task": "credit.due_reminders",
                "schedule": crontab(hour="8", minute="0"),  # 08:00 Africa/Cairo
            },
        },
    )

    flask_app = create_app()

    class ContextTask(celery.Task):  # type: ignore[misc]
        abstract = True

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery_app = _make_celery()

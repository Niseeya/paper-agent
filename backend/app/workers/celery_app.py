"""Celery 应用占位。解析/导出任务后续接入。"""

import os

from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("paper_agent", broker=redis_url, backend=redis_url)
celery_app.conf.task_routes = {"backend.app.workers.*": {"queue": "default"}}

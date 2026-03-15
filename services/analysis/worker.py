"""
CodeSage Analysis Worker
Celery worker for processing analysis tasks
"""

import os

import structlog
from celery import Celery
from celery.signals import task_failure, task_postrun, task_prerun
from prometheus_client import Counter, Histogram, start_http_server

from core.config import settings

logger = structlog.get_logger()

# Initialize Celery
app = Celery(
    "codesage_analysis",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=[
        "tasks.analysis_tasks",
        "engine.ast_parser",
        "engine.security_scanner",
        "engine.performance_analyzer",
        "engine.taint_analysis",
    ],
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.MAX_ANALYSIS_TIME,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    task_routes={
        "tasks.analysis_tasks.analyze_repository": {"queue": "analysis"},
        "tasks.analysis_tasks.analyze_file": {"queue": "analysis"},
        "tasks.analysis_tasks.security_scan": {"queue": "security"},
        "tasks.analysis_tasks.performance_analysis": {"queue": "performance"},
    },
)

# Prometheus metrics
TASKS_PROCESSED = Counter(
    "analysis_tasks_processed_total",
    "Total number of analysis tasks processed",
    ["task_type", "status"],
)

TASK_DURATION = Histogram(
    "analysis_task_duration_seconds",
    "Time spent processing analysis tasks",
    ["task_type"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)


@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs):
    """Log task start"""
    logger.info(
        "Task started",
        task_id=task_id,
        task_name=task.name,
    )


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state):
    """Log task completion"""
    logger.info(
        "Task completed",
        task_id=task_id,
        task_name=task.name,
        state=state,
    )
    TASKS_PROCESSED.labels(task_type=task.name.split(".")[-1], status=state.lower()).inc()


@task_failure.connect
def task_failure_handler(sender, task_id, exception, args, kwargs, traceback, einfo):
    """Log task failure"""
    logger.error(
        "Task failed",
        task_id=task_id,
        exception=str(exception),
        traceback=traceback,
    )
    TASKS_PROCESSED.labels(task_type=sender.name.split(".")[-1], status="failure").inc()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks"""
    # Health check every 30 seconds
    sender.add_periodic_task(30.0, health_check.s(), name="health-check")


@app.task(bind=True)
def health_check(self):
    """Health check task"""
    return {"status": "healthy", "worker": self.request.hostname}


def start_metrics_server():
    """Start Prometheus metrics server"""
    port = int(os.getenv("METRICS_PORT", "8080"))
    start_http_server(port)
    logger.info(f"Metrics server started on port {port}")


if __name__ == "__main__":
    # Start metrics server
    start_metrics_server()
    
    # Start worker
    app.start()

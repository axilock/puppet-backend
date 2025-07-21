"""
Celery configuration for the distributed task processing system.
"""

from celery import Celery

from .config import get_broker_url, QUEUE_NAMES

# Create Celery app
app = Celery('distributed_task_system')

# Configure Celery

app.conf.update(
    broker_url=get_broker_url(),
    result_backend=get_broker_url(),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'distributed_task_system.worker.tasks.process_task': {
            'queue': lambda task_args, task_kwargs, options: (
                QUEUE_NAMES.get(task_kwargs.get('task_type'), QUEUE_NAMES['default'])
            )
        }
    },
    task_default_queue=QUEUE_NAMES['default'],
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    task_acks_late=True,  # Acknowledge task after it's completed
    task_reject_on_worker_lost=True,  # Reject task if worker is lost
    task_time_limit=1800,  # 30 minutes
)
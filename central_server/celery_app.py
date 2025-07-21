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
      # Routes the tasks.process_task function to different queues based on task type
    task_routes={
        'tasks.process_task': {  # Task name to execute
            'queue': lambda task_args, task_kwargs, options: (
                task_kwargs.get('task_type')
            )
        }
    },
    task_default_queue=QUEUE_NAMES['default'],
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    task_acks_late=True,  # Acknowledge task after it's completed
    task_time_limit=1800,  # 30 minutes
)
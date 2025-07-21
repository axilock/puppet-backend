"""
Configuration settings for the distributed task processing system.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# MongoDB configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'task_processing_system')

# API Server configuration
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 8000))

# Queue names
QUEUE_NAMES = { 'default': 'default_queue' }

# Broker URL for Celery
def get_broker_url():
    """Generate the broker URL for Celery based on Redis configuration."""
    auth = f":{REDIS_PASSWORD}@" if REDIS_PASSWORD else ""
    return f"redis://{auth}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# MongoDB collections
COLLECTIONS = {
    'tasks': 'tasks',
    'workers': 'workers',
    'plugins': 'plugins',
    'results': 'results',
}

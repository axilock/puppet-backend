import logging
import os
import sys
import threading
import time

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
import redis
from pymongo.errors import PyMongoError

# Use relative imports when running directly, absolute imports when imported as a module
try:
    # Try relative imports first (for direct execution)
    from config import API_HOST, API_PORT
    from db import db_client
    from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
    from api import app
except ImportError:
    # Fall back to absolute imports (for module import)
    from .config import API_HOST, API_PORT
    from .db import db_client
    from .config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
    from .api import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_database_connection() -> bool:
    """Check if the MongoDB database is accessible."""
    try:
        # Try to ping the database
        db_client.client.admin.command('ping')
        return True
    except PyMongoError as e:
        logger.error(f"Database connection error: {e}")
        return False


def check_redis_connection() -> bool:
    """Check if Redis is accessible."""
    try:
        # Get Redis connection parameters from Celery's broker_url
        print( REDIS_HOST,REDIS_PORT,REDIS_DB,REDIS_PASSWORD )
        
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD
        )
        # Ping Redis to check if it's accessible
        redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        return False


def monitor_system_health() -> None:
    """Monitor the health of the system components."""
    while True:
        try:
            # Check database connection
            db_healthy = check_database_connection()
            
            # Check Redis connection
            redis_healthy = check_redis_connection()
            
            # Log status
            if db_healthy and redis_healthy:
                logger.info("System health check: All components healthy")
            else:
                components = []
                if not db_healthy:
                    components.append("MongoDB")
                if not redis_healthy:
                    components.append("Redis")
                logger.warning(f"System health check: Issues with {', '.join(components)}")
            
            # Sleep for 60 seconds
            time.sleep(60)
        except Exception as e:
            logger.error(f"Error in health monitoring: {e}")
            time.sleep(60)


def start_health_monitor() -> None:
    """Start the health monitoring thread."""
    thread = threading.Thread(target=monitor_system_health, daemon=True)
    thread.start()
    logger.info("Health monitoring started")


def main() -> None:
    """Main entry point for the central server."""
    logger.info("Starting central server...")
    
    # Check initial connections
    if not check_database_connection():
        logger.error("Cannot connect to MongoDB. Please check the connection.")
        sys.exit(1)
    
    if not check_redis_connection():
        logger.error("Cannot connect to Redis. Please check the connection.")
        sys.exit(1)
    
    # Start health monitoring
    start_health_monitor()
    
    # Start the API server
    logger.info(f"Starting API server on {API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    main()

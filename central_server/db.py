"""
Database utilities for the distributed task processing system.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId

from .config import MONGO_URI, MONGO_DB_NAME, COLLECTIONS
from .models import Task, Worker, Plugin, TaskResult, WorkerMetrics

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseClient:
    """Client for interacting with the MongoDB database."""

    def __init__(self, uri: str = MONGO_URI, db_name: str = MONGO_DB_NAME):
        """Initialize the database client."""
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        
        # Initialize collections
        self.tasks: Collection = self.db[COLLECTIONS['tasks']]
        self.workers: Collection = self.db[COLLECTIONS['workers']]
        self.plugins: Collection = self.db[COLLECTIONS['plugins']]
        self.results: Collection = self.db[COLLECTIONS['results']]
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes on collections."""
        # Task indexes
        self.tasks.create_index("status")
        self.tasks.create_index("type")
        self.tasks.create_index("worker_id")
        
        # Worker indexes
        self.workers.create_index("hostname")
        self.workers.create_index("status")
        self.workers.create_index("last_heartbeat")
        
        # Plugin indexes
        self.plugins.create_index("id", unique=True)
        self.plugins.create_index([("id", 1), ("version", 1)], unique=True)
        
        # Results indexes
        self.results.create_index("task_id")
        self.results.create_index("worker_id")
        self.results.create_index("completed_at")

    # Task operations
    def create_task(self, task: Task) -> str:
        """Create a new task in the database."""
        try:
            task_dict = task.dict()
            # Ensure the task has an id field (should be a UUID)
            task_id = task_dict.get("id")
            if not task_id:
                logger.error("Task missing id field")
                raise ValueError("Task must have an id field")
                
            result = self.tasks.insert_one(task_dict)
            return task_id
        except PyMongoError as e:
            logger.error(f"Error creating task: {e}")
            raise

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        try:
            # First try to find by id field (UUID), excluding _id field
            task = self.tasks.find_one({"id": task_id}, {"_id": 0})
            if task:
                return task
                
            # If not found, try legacy _id field (ObjectId)
            try:
                # Convert ObjectId to string id and exclude _id from results
                task = self.tasks.find_one({"_id": ObjectId(task_id)})
                if task:
                    task["id"] = str(task.pop("_id"))
                return task
            except:
                return None
        except PyMongoError as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None

    def update_task(self, task_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a task in the database."""
        try:
            # First try to update by id field (UUID)
            result = self.tasks.update_one(
                {"id": task_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                return True
                
            # If not found, try legacy _id field (ObjectId)
            try:
                result = self.tasks.update_one(
                    {"_id": ObjectId(task_id)},
                    {"$set": update_data}
                )
                return result.modified_count > 0
            except:
                return False
        except PyMongoError as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return False

    def get_pending_tasks(self, task_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get pending tasks, optionally filtered by type."""
        query = {"status": "pending"}
        if task_type:
            query["type"] = task_type
        
        try:
            # Exclude _id field from results
            tasks = list(self.tasks.find(query, {"_id": 0}).limit(limit))
            return tasks
        except PyMongoError as e:
            logger.error(f"Error getting pending tasks: {e}")
            return []

    # Worker operations
    def register_worker(self, worker: Worker) -> str:
        """Register a new worker or update an existing one."""
        try:
            worker_dict = worker.dict()
            result = self.workers.update_one(
                {"id": worker.id},
                {"$set": worker_dict},
                upsert=True
            )
            return worker.id
        except PyMongoError as e:
            logger.error(f"Error registering worker: {e}")
            raise

    def update_worker_status(self, worker_id: str, status: str, resources: Dict[str, Any]) -> bool:
        """Update a worker's status and resource information."""
        try:
            result = self.workers.update_one(
                {"id": worker_id},
                {
                    "$set": {
                        "status": status,
                        "resources": resources,
                        "last_heartbeat": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error updating worker status for {worker_id}: {e}")
            return False

    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get a worker by ID."""
        try:
            return self.workers.find_one({"id": worker_id}, {"_id": 0})
        except PyMongoError as e:
            logger.error(f"Error getting worker {worker_id}: {e}")
            return None

    def get_active_workers(self) -> List[Dict[str, Any]]:
        """Get all active workers."""
        try:
            # Consider workers offline if no heartbeat in the last 5 minutes
            cutoff_time = datetime.utcnow().timestamp() - 300  # 5 minutes
            return list(self.workers.find({
                "last_heartbeat": {"$gt": cutoff_time},
                "status": {"$ne": "offline"}
            }, {"_id": 0}))
        except PyMongoError as e:
            logger.error(f"Error getting active workers: {e}")
            return []

    # Plugin operations
    def register_plugin(self, plugin: Plugin) -> bool:
        """Register a new plugin or update an existing one."""
        try:
            plugin_dict = plugin.dict()
            result = self.plugins.update_one(
                {"id": plugin.id, "version": plugin.version},
                {"$set": plugin_dict},
                upsert=True
            )
            return True
        except PyMongoError as e:
            logger.error(f"Error registering plugin: {e}")
            return False

    def get_plugin(self, plugin_id: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a plugin by ID and optionally version."""
        try:
            query = {"id": plugin_id}
            if version:
                query["version"] = version
                return self.plugins.find_one(query, {"_id": 0})
            else:
                # Get the latest version if no version specified
                return self.plugins.find_one(
                    {"id": plugin_id},
                    {"_id": 0, "created_at": 0, "updated_at": 0},
                    sort=[("version", -1)]
                )
        except PyMongoError as e:
            logger.error(f"Error getting plugin {plugin_id}: {e}")
            return None

    def get_all_plugins(self) -> List[Dict[str, Any]]:
        """Get all plugins, latest version of each."""
        try:
            # This is a bit tricky - we need to get the latest version of each plugin
            pipeline = [
                {"$sort": {"id": 1, "version": -1}},
                {"$group": {
                    "_id": "$id",
                    "latest": {"$first": "$$ROOT"}
                }},
                {"$replaceRoot": {"newRoot": "$latest"}},
                {"$project": {
                    "_id": 0,           # Exclude _id
                    "created_at": 0,    # Exclude created_at  
                    "updated_at": 0     # Exclude updated_at
                }}
            ]
            return list(self.plugins.aggregate(pipeline))
        except PyMongoError as e:
            logger.error(f"Error getting all plugins: {e}")
            return []

    # Result operations
    def store_task_result(self, result: TaskResult) -> bool:
        """Store a task result."""
        try:
            result_dict = result.dict()
            self.results.insert_one(result_dict)
            
            # Also update the task with the result
            self.tasks.update_one(
                {"id": result.task_id},
                {
                    "$set": {
                        "status": "completed" if result.success else "failed",
                        "result": result.data,
                        "error": result.error,
                        "completed_at": result.completed_at
                    }
                }
            )
            return True
        except PyMongoError as e:
            logger.error(f"Error storing task result: {e}")
            return False

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the result for a task."""
        try:
            return self.results.find_one({"task_id": task_id}, {"_id": 0})
        except PyMongoError as e:
            logger.error(f"Error getting result for task {task_id}: {e}")
            return None

    # Metrics operations
    def store_worker_metrics(self, metrics: WorkerMetrics) -> bool:
        """Store worker metrics."""
        try:
            metrics_dict = metrics.dict()
            self.db.worker_metrics.insert_one(metrics_dict)
            return True
        except PyMongoError as e:
            logger.error(f"Error storing worker metrics: {e}")
            return False

    def get_worker_metrics(self, worker_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metrics for a worker."""
        try:
            return list(self.db.worker_metrics.find(
                {"worker_id": worker_id},
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit))
        except PyMongoError as e:
            logger.error(f"Error getting metrics for worker {worker_id}: {e}")
            return []


# Create a singleton instance
db_client = DatabaseClient()

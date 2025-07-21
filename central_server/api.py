"""
FastAPI server for the central task processing system.
"""
import logging
import uuid
import secrets
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Body, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import sys
import os
# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use relative imports when running directly, absolute imports when imported as a module
try:
    # Try relative imports first (for direct execution)
    from models import Task, Worker, Plugin, TaskInput, TaskResult, WorkerMetrics, WorkerResources, WorkerStatus
    from db import db_client
    from celery_app import app as celery_app
    from config import AUTH_USERNAME, AUTH_PASSWORD
except ImportError:
    # Fall back to absolute imports (for module import)
    from .models import Task, Worker, Plugin, TaskInput, TaskResult, WorkerMetrics, WorkerResources, WorkerStatus
    from .db import db_client
    from .celery_app import app as celery_app
    from .config import AUTH_USERNAME, AUTH_PASSWORD

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Distributed Task Processing API")

# Setup HTTP Basic Auth
security = HTTPBasic()

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify HTTP Basic Auth credentials."""
    # Compare with credentials from config
    is_username_correct = secrets.compare_digest(credentials.username, AUTH_USERNAME)
    is_password_correct = secrets.compare_digest(credentials.password, AUTH_PASSWORD)
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": 'Basic realm="login", charset="UTF-8"'},
        )
    return credentials.username

# Helper function to get the static directory path
def get_static_dir():
    """
    Get the path to the static files directory.
    In Docker, static files are in /app/static
    In local development, they're in central_server/static or static
    """
    if os.path.exists("/app/static"):
        return "/app/static"
    elif os.path.exists("static"):
        return "static"
    else:
        return "central_server/static"

# Mount static files
static_dir = get_static_dir()
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=FileResponse)
async def serve_index(username: str = Depends(verify_auth)):
    static_dir = get_static_dir()
    return FileResponse(f"{static_dir}/index.html")

@app.get("/{filename}.html", response_class=FileResponse)
async def serve_html_file(filename: str, username: str = Depends(verify_auth)):
    static_dir = get_static_dir()
    file_path = f"{static_dir}/{filename}.html"
    return FileResponse(file_path)

@app.get("/{filename}.js", response_class=FileResponse)
async def serve_html_file(filename: str):
    static_dir = get_static_dir()
    file_path = f"{static_dir}/{filename}.js"
    return FileResponse(file_path)

# Task submission endpoints
@app.post("/api/tasks", response_model=Dict[str, str])
async def create_task(task_input: TaskInput, username: str = Depends(verify_auth)):
    """Create a new task and add it to the queue."""
    try:
        # Create a unique ID for the task
        task_id = str(uuid.uuid4())
        
        # Create the task object
        task = Task(
            id=task_id,
            type=task_input.type,
            input_data=task_input.data,
            plugin_id=task_input.plugin_id,
            plugin_parameters=task_input.plugin_parameters,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        # Store the task in the database
        db_client.create_task(task)
        

        task_data = task.dict()

        celery_app.send_task(
            'tasks.process_task',       # Task name to execute
            kwargs={
                'task_data': task_data,
                'worker_id': None, 
                'task_type': task.type 
            },
            queue=task.type             # Message gets placed in the queue named task.type (e.g., "image_processing" queue)

        )
        
        logger.info(f"Task {task_id} created and added to queue {task.type}")
        
        # Return the task ID
        return {"task_id": task_id}
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{task_id}", response_model=Dict[str, Any])
async def get_task(task_id: str, username: str = Depends(verify_auth)):
    """Get a task by ID."""
    # The get_task method in db.py already excludes _id
    task = db_client.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/tasks", response_model=List[Dict[str, Any]])
async def list_tasks(
    status: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    sort: str = "created_at",
    order: str = "desc",
    username: str = Depends(verify_auth)
):
    """List tasks with optional filtering."""
    query = {}
    if status:
        query["status"] = status
    if type:
        query["type"] = type
    
    try:
        # Determine sort direction
        sort_direction = -1 if order.lower() == "desc" else 1
        
        # Exclude _id field from results
        tasks = list(db_client.tasks.find(query, {"_id": 0})
                    .sort(sort, sort_direction)
                    .skip(skip)
                    .limit(limit))
        return tasks
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Worker endpoints
@app.post("/api/workers/register", response_model=Dict[str, str])
async def register_worker(worker: Worker, username: str = Depends(verify_auth)):
    """Register a new worker or update an existing one."""
    try:
        worker_id = db_client.register_worker(worker)
        return {"worker_id": worker_id}
    except Exception as e:
        logger.error(f"Error registering worker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workers/{worker_id}/heartbeat")
async def worker_heartbeat(
    worker_id: str,
    status: str = Body(...),  
    resources: dict = Body(...),
    username: str = Depends(verify_auth)
):
    """Update a worker's heartbeat and status."""
    try:
        success = db_client.update_worker_status(
            worker_id,
            status,
            resources
        )
        if not success:
            raise HTTPException(status_code=404, detail="Worker not found")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating worker heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workers", response_model=List[Dict[str, Any]])
async def list_workers(status: Optional[str] = None, username: str = Depends(verify_auth)):
    """List all workers, optionally filtered by status."""
    try:
        query = {}
        if status:
            query["status"] = status
        
        # Exclude _id field from results
        workers = list(db_client.workers.find(query, {"_id": 0}))
        return workers
    except Exception as e:
        logger.error(f"Error listing workers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workers/{worker_id}", response_model=Dict[str, Any])
async def get_worker(worker_id: str, username: str = Depends(verify_auth)):
    """Get a worker by ID."""
    # The get_worker method in db.py already excludes _id with {"_id": 0}
    worker = db_client.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker

@app.post("/api/workers/{worker_id}/queues")
async def update_worker_queues(worker_id: str, queues: List[str], username: str = Depends(verify_auth)):
    """Update the queues a worker consumes from."""
    try:
        result = db_client.workers.update_one(
            {"id": worker_id},
            {"$set": {"queues": queues}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Worker not found")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error updating worker queues: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Plugin endpoints
@app.post("/api/plugins", response_model=Dict[str, str])
async def register_plugin(plugin: Plugin, username: str = Depends(verify_auth)):
    """Register a new plugin or update an existing one."""
    try:
        # Generate a UUID for the plugin ID if not provided or empty
        if not plugin.id:
            plugin.id = str(uuid.uuid4())
        
        success = db_client.register_plugin(plugin)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to register plugin")
        return {"status": "ok", "plugin_id": plugin.id}
    except Exception as e:
        logger.error(f"Error registering plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/plugins", response_model=List[Dict[str, Any]])
async def list_plugins(username: str = Depends(verify_auth)):
    """List all plugins (latest version of each)."""
    try:
        # The get_all_plugins method in db.py already excludes _id
        plugins = db_client.get_all_plugins()
        return plugins
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/plugins/{plugin_id}", response_model=Dict[str, Any])
async def get_plugin(plugin_id: str, version: Optional[str] = None, username: str = Depends(verify_auth)):
    """Get a plugin by ID and optionally version."""
    # The get_plugin method in db.py already excludes _id
    plugin = db_client.get_plugin(plugin_id, version)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return plugin

# Task result endpoints
@app.post("/api/results", response_model=Dict[str, str])
async def submit_task_result(result: TaskResult, username: str = Depends(verify_auth)):
    """Submit the result of a completed task."""
    try:
        success = db_client.store_task_result(result)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store task result")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error submitting task result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/results/{task_id}", response_model=Dict[str, Any])
async def get_task_result(task_id: str, username: str = Depends(verify_auth)):
    """Get the result for a task."""
    # The get_task_result method in db.py already excludes _id
    result = db_client.get_task_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result

@app.post("/api/tasks/{task_id}/status", response_model=Dict[str, str])
async def update_task_status(
    task_id: str,
    status: str = Body(...),
    worker_id: Optional[str] = Body(None),
    started_at: Optional[datetime] = Body(None),
    username: str = Depends(verify_auth)
):
    """Update the status of a task."""
    try:
        update_data = {"status": status}
        if worker_id:
            update_data["worker_id"] = worker_id
        if started_at:
            update_data["started_at"] = started_at
        
        # If the task is being marked as in_process, update the started_at time if not provided
        if status == "in_process" and not started_at:
            update_data["started_at"] = datetime.utcnow()
        
        # Update the task directly in the collection using the id field, not _id
        result = db_client.tasks.update_one(
            {"id": task_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Metrics endpoints
@app.post("/api/metrics/worker", response_model=Dict[str, str])
async def submit_worker_metrics(metrics: WorkerMetrics, username: str = Depends(verify_auth)):
    """Submit metrics from a worker."""
    try:
        success = db_client.store_worker_metrics(metrics)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store worker metrics")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error submitting worker metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics/worker/{worker_id}", response_model=List[Dict[str, Any]])
async def get_worker_metrics(worker_id: str, limit: int = 100, username: str = Depends(verify_auth)):
    """Get recent metrics for a worker."""
    try:
        # The get_worker_metrics method in db.py already excludes _id
        metrics = db_client.get_worker_metrics(worker_id, limit)
        return metrics
    except Exception as e:
        logger.error(f"Error getting worker metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System status endpoint
@app.get("/api/status", response_model=Dict[str, Any])
async def get_system_status(username: str = Depends(verify_auth)):
    """Get overall system status."""
    try:
        # Get counts of tasks by status
        task_counts = {}
        for status in ["pending", "in_process", "completed", "failed", "manual_review"]:
            task_counts[status] = db_client.tasks.count_documents({"status": status})
        
        # Get counts of workers by status
        worker_counts = {}
        for status in ["active", "idle", "offline"]:
            worker_counts[status] = db_client.workers.count_documents({"status": status})
        
        # Get plugin count
        plugin_count = len(db_client.get_all_plugins())
        
        status_data = {
            "tasks": task_counts,
            "workers": worker_counts,
            "plugins": plugin_count,
            "timestamp": datetime.utcnow()
        }
        
        return status_data
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check(username: str = Depends(verify_auth)):
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    try:
        # Try relative imports first (for direct execution)
        from config import API_HOST, API_PORT
    except ImportError:
        # Fall back to absolute imports (for module import)
        from .config import API_HOST, API_PORT
    
    uvicorn.run(app, host=API_HOST, port=API_PORT)

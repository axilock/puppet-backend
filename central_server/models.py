"""
Database models for the distributed task processing system.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Enum representing the possible states of a task."""
    PENDING = "pending"
    IN_PROCESS = "in_process"
    COMPLETED = "completed"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"


class WorkerStatus(str, Enum):
    """Enum representing the possible states of a worker."""
    ACTIVE = "active"
    IDLE = "idle"
    OFFLINE = "offline"


class PluginParameter(BaseModel):
    """Model representing a parameter for a plugin."""
    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None


class Plugin(BaseModel):
    """Model representing a plugin in the system."""
    id: str = Field("", description="Unique identifier for the plugin (auto-generated if not provided)")
    name: str = Field(..., description="Human-readable name of the plugin")
    version: str = Field(..., description="Semantic version of the plugin")
    docker_image: str = Field(..., description="Docker image name and tag")
    description: str = Field(..., description="Description of what the plugin does")
    parameters: List[PluginParameter] = Field(default_factory=list, description="Parameters accepted by the plugin")
    queue: Optional[str] = Field(None, description="Queue name this plugin processes tasks from")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskInput(BaseModel):
    """Model representing the input for a task."""
    type: str = Field(..., description="Type of task (domain, repository, etc.)")
    data: Dict[str, Any] = Field(..., description="Input data for the task")
    plugin_id: str = Field(..., description="ID of the plugin to use for processing")
    plugin_parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the plugin")


class Task(BaseModel):
    """Model representing a task in the system."""
    id: str = Field(..., description="Unique identifier for the task")
    type: str = Field(..., description="Type of task (domain, repository, etc.)")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    input_data: Dict[str, Any] = Field(..., description="Input data for the task")
    plugin_id: str = Field(..., description="ID of the plugin used for processing")
    plugin_parameters: Dict[str, Any] = Field(default_factory=dict)
    worker_id: Optional[str] = Field(None, description="ID of the worker processing this task")
    attempt_count: int = Field(default=0, description="Number of processing attempts")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data from processing")
    error: Optional[str] = Field(None, description="Error message if task failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkerResources(BaseModel):
    """Model representing resource usage of a worker."""
    ram_total: float = Field(..., description="Total RAM in GB")
    ram_available: float = Field(..., description="Available RAM in GB")
    cpu_usage: float = Field(..., description="CPU usage percentage")


class Worker(BaseModel):
    """Model representing a worker in the system."""
    id: str = Field(..., description="Unique identifier for the worker")
    hostname: str = Field(..., description="Hostname of the machine running the worker")
    ip: str = Field(..., description="IP address of the worker")
    status: WorkerStatus = Field(default=WorkerStatus.IDLE)
    resources: WorkerResources
    active_tasks: List[str] = Field(default_factory=list, description="IDs of tasks being processed")
    plugins: Dict[str, str] = Field(default_factory=dict, description="Map of plugin IDs to versions")
    queues: List[str] = Field(default_factory=list, description="Queue names this worker consumes from")
    registered_at: str = Field(..., description="datetime register time")


class TaskResult(BaseModel):
    """Model representing the result of a task."""
    task_id: str
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    processing_time: float  # in seconds
    worker_id: str
    completed_at: str


class WorkerMetrics(BaseModel):
    """Model representing metrics reported by a worker."""
    worker_id: str
    hostname: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ram_usage_percent: float
    cpu_usage_percent: float
    tasks_processed: int
    tasks_succeeded: int
    tasks_failed: int
    active_task_count: int

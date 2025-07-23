# Distributed Task Processing System

A flexible, distributed system for processing various types of tasks at scale using Python, Redis, MongoDB, and Docker.

## Overview

This system allows you to:

- Process any type of items (domains, repositories, Docker images, URLs, files, etc.) at scale
- Handle 100,000+ items across multiple computers
- Use plugin-based workflows for different processing types
- Distribute work across many computers
- Automatically update with new workflows
- Dynamically configure workers with new queues as plugins are added

## Architecture

The system consists of the following components:

1. **Central Server**
   - API server for task submission, worker registration, and status reporting
   - Task queue using Redis and Celery
   - MongoDB database for storing task data, results, and system state

2. **Workers**
   - Standalone processes that can be run on any machine
   - Connect to the central server to pull tasks
   - Execute tasks using Docker-based plugins
   - Report metrics and status back to the central server

3. **Plugins**
   - Docker-based containers that implement specific processing logic
   - Can be added and updated without modifying the core system
   - Automatically distributed to workers

4. **Admin Dashboard**
   - Web interface for monitoring the system
   - View tasks, workers, and plugins
   - Track system metrics and performance

## Requirements

- Python 3.9+
- Redis
- MongoDB
- Docker
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/distributed-task-system.git
   cd distributed-task-system
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Make sure Redis and MongoDB are running:
   ```bash
   # Start Redis (example for Linux)
   redis-server

   # Start MongoDB (example for Linux)
   mongod --dbpath /path/to/data/db
   ```

## Configuration

The system can be configured by setting environment variables or by creating a `.env` file in the project root directory. The following variables can be configured:

- `REDIS_HOST`: Redis host (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)
- `REDIS_PASSWORD`: Redis password (default: None)
- `MONGO_URI`: MongoDB connection URI (default: mongodb://localhost:27017/)
- `MONGO_DB_NAME`: MongoDB database name (default: task_processing_system)
- `API_HOST`: API server host (default: 0.0.0.0)
- `API_PORT`: API server port (default: 8000)

## Running the System

### Starting the Central Server

```bash
# Start the API server
python -m distributed_task_system.central_server.main
```

### Starting the Admin Dashboard

```bash
# Start the admin dashboard
python -m distributed_task_system.admin_dashboard.app
```

### Starting Workers

```bash
# Start a worker with 4 processes
python -m distributed_task_system.worker.worker --server localhost:8000 --workers 4
```

You can start multiple workers on different machines by specifying the central server address:

```bash
python -m distributed_task_system.worker.worker --server central-server-address:8000 --workers 4
```

To have workers process only specific types of tasks, you can specify the queues:

```bash
python -m distributed_task_system.worker.worker --server localhost:8000 --workers 2 --queues domain_queue,repository_queue
```

## Creating Plugins

Plugins are Docker containers that follow a specific contract:

1. Read input data from `/input/input.json`
2. Read parameters from `/input/parameters.json`
3. Write results to `/output/result.json`
4. Exit with code 0 on success, non-zero on failure
5. Write error messages to stderr

See the `plugins/example_plugin` directory for an example plugin.

### Dynamic Queue Configuration

Plugins can specify which queue they process tasks from. When a plugin is registered or updated, the system automatically configures workers to consume from this queue. This allows new plugins to seamlessly integrate with the system without requiring manual worker configuration.

To specify a queue for a plugin, include a `queue` field in the plugin registration:

```json
{
  "id": "example-plugin",
  "name": "Example Plugin",
  "version": "1.0.0",
  "docker_image": "example-plugin:1.0.0",
  "description": "An example plugin",
  "queue": "domain_queue",
  "parameters": [...]
}
```

Workers will automatically be updated to consume from this queue during their next heartbeat cycle.

### Building and Registering a Plugin

1. Build the Docker image:
   ```bash
   cd plugins/example_plugin
   docker build -t example-plugin:1.0.0 .
   ```

2. Register the plugin with the central server:
   ```bash
   curl -X POST http://localhost:8000/api/plugins \
     -H "Content-Type: application/json" \
     -d '{
       "id": "example-plugin",
       "name": "Example Plugin",
       "version": "1.0.0",
       "docker_image": "example-plugin:1.0.0",
       "description": "An example plugin",
       "queue": "example_queue",
       "parameters": [
         {
           "name": "param1",
           "type": "string",
           "description": "Example parameter",
           "required": false,
           "default": "default-value"
         }
       ]
     }'
   ```

## Submitting Tasks

Tasks can be submitted to the system using the API:

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "domain",
    "data": {
      "domain": "example.com"
    },
    "plugin_id": "example-plugin",
    "plugin_parameters": {
      "param1": "value1"
    }
  }'
```

## Monitoring

The admin dashboard provides a web interface for monitoring the system. Open a web browser and navigate to:

```
http://localhost:8080
```


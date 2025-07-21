# Distributed Task System - Dockerized

This repository contains a distributed task processing system with two main components:
1. Central Server (dockerized)
2. Worker (runs locally)

## Prerequisites

- Docker and Docker Compose
- Python 3.9+
- pip

## Setup

### 1. Configure Environment Variables

Rename the `.env.example` to `.env` and customize your configuration :

```
# MongoDB configuration
MONGO_USER=admin
MONGO_PASSWORD=password
MONGO_DB_NAME=task_processing_system

# Redis configuration
REDIS_PASSWORD=redispassword
REDIS_PORT=6379

# API Server configuration
API_PORT=8000
```

### 2. Start the Dockerized Central Server

Run the following command to start MongoDB, Redis, and the central server:

```bash
docker-compose up -d
```

This will:
- Start MongoDB container
- Start Redis container with password authentication
- Build and start the central server container

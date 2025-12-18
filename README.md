# Sentinel — Distributed Task Execution System

Sentinel is a **distributed, asynchronous task execution system** inspired by platforms like **Celery** and **Google Cloud Tasks**.  
It allows clients to submit computational tasks via a REST API, enqueue them with priorities, and execute them asynchronously using scalable worker nodes.

This project demonstrates **distributed systems fundamentals**, **backend engineering**, and **production-style system design**, making it ideal for **Microsoft & Google internship applications**.

---

##  Key Features

-  Asynchronous task execution (producer–consumer model)
-  Priority-based scheduling using Redis Sorted Sets
-  Horizontally scalable workers
-  Centralized task state & metrics
-  REST API with OpenAPI documentation
-  Fully containerized using Docker & Docker Compose

---

##  System Architecture
```sql
+----------+
|  Client  |
+----------+
     |
     | HTTP
     v
+----------------------+
|   FastAPI (API)      |
|  - Submit Task       |
|  - Get Stats         |
+----------------------+
     |
     | Redis (Queue + State)
     v
+----------------------+
|        Redis         |
|  - Sorted Set Queue  |
|  - Task Status       |
|  - Metrics Counters  |
+----------------------+
     |
     v
+----------------------+
|   Worker Pool        |
|  +----------------+ |
|  |    Worker 1    | |
|  +----------------+ |
|  |    Worker 2    | |
|  +----------------+ |
|  |    Worker N    | |
|  +----------------+ |
|    Execute Tasks    |
+----------------------+

```

---

##  Design Decisions

### Why Redis?
- Extremely fast, in-memory data store
- Redis **Sorted Sets** naturally implement priority queues
- Centralized shared state for API & workers
- Widely used in real-world distributed systems

### Task Scheduling Strategy
- Tasks are stored in a Redis Sorted Set
- Score calculation:
score= (-priority*LARGE_CONSTANT)+timestamp
- Guarantees:
- Higher-priority tasks execute first
- FIFO order for tasks with the same priority

### Delivery Semantics
- **At-least-once delivery**
- Tasks may retry on failure
- Suitable for idempotent workloads

---

## API Endpoints

### ➕ Submit Task
**POST /submit-task**

Request:
```json
{
"payload": { "job": "example-task" },
"priority": 5
}
```

Response:
```json
{
  "task_id": "uuid",
  "status": "QUEUED"
}
```

---

## System Statistics

### GET /stats
Response:
```json
{
  "queue_size": 0,
  "status_counts": {
    "QUEUED": 0,
    "IN_PROGRESS": 1,
    "COMPLETED": 2,
    "FAILED": 0
  }
}
```
---

## Running the Project Locally
Prerequisites
- Docker
- Docker Compose (or Colima + Docker CLI on macOS)

Start the System:
```bash
docker compose up --build
```

Open API Documentation: 
```bash
http://localhost:8000/docs
```

---

### Scaling Workers
Sentinel supports horizontal scaling of workers.
```bash
docker compose up --scale worker=3
```

---

## Fault Tolerance Demonstration
- Submit tasks via the API
- Kill a worker container while tasks are processing
- Remaining workers continue execution
- Tasks remain safe in Redis until completed
This demonstrates resilience to worker failures.

---

## Project Structure
```bash
sentinel/
├── api/                # FastAPI service
│   ├── main.py
│   └── Dockerfile
├── worker/             # Background task workers
│   ├── worker.py
│   └── Dockerfile
├── common/             # Shared logic
│   ├── models.py
│   ├── redis_queue.py
│   └── __init__.py
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Future Improvements
- Retry logic with exponential backoff
- Dead-letter queue for failed tasks
- Task result persistence
- Authentication & rate limiting
- Real-time monitoring dashboard
- Exactly-once execution guarantees

---

## What This Project Demonstrates
- Distributed systems architecture
- Asynchronous processing
- Priority queue design
- Redis as a message broker
- Dockerized microservices
- Production-grade backend practices

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from common.models import Task
from common.redis_queue import REDIS_DB, REDIS_HOST, REDIS_PORT, QUEUE_KEY, enqueue_task, get_stats


app = FastAPI(title="Sentinel Task API")


@app.on_event("startup")
async def log_redis_config() -> None:
    print(
        f"[api] Redis connection host={REDIS_HOST} port={REDIS_PORT} db={REDIS_DB}",
        flush=True,
    )


class SubmitTaskRequest(BaseModel):
    """Schema for incoming task submissions.

    - `payload` is arbitrary JSON data needed to execute the task.
    - `priority` is optional; if omitted, a default will be used.
    """

    payload: Dict[str, Any]
    priority: Optional[int] = None


class SubmitTaskResponse(BaseModel):
    """Schema for the response returned after enqueuing a task."""

    task_id: str
    status: str


class StatsResponse(BaseModel):
    """Schema for basic system statistics returned by /stats."""

    total_tasks_submitted: int
    completed_tasks: int
    failed_tasks: int
    tasks_in_queue: int


@app.post("/submit-task", response_model=SubmitTaskResponse)
async def submit_task(request: SubmitTaskRequest) -> SubmitTaskResponse:
    """Accept a new task request and enqueue it for background processing.

    Request flow:
    1. FastAPI parses the incoming JSON into a `SubmitTaskRequest` object.
    2. We create a new `Task` domain object with a unique ID and timestamps.
    3. We push the task into the Redis-backed queue using the queue module.
    4. We return a simple JSON response containing the new task ID and status.
    """
    # Step 1: Extract data from the validated request model.
    print(f"[api] Submitting task using Redis key={QUEUE_KEY}", flush=True)
    payload = request.payload
    priority = request.priority if request.priority is not None else 0

    # Step 2: Create a new Task instance.
    task = Task(
        id=str(uuid.uuid4()),
        payload=payload,
        priority=priority,
        retries=0,
        status="QUEUED",
        created_at=time.time(),
    )

    # Step 3: Enqueue the task into Redis.
    # `enqueue_task` is synchronous, so we offload it to a thread to avoid
    # blocking the asyncio event loop.
    print(f"[api] Calling enqueue_task for task_id={task.id}", flush=True)
    try:
        await asyncio.to_thread(enqueue_task, task)
    except Exception as exc:
        print(f"[api] enqueue_task failed for task_id={task.id}: {exc}", flush=True)
        raise
    print(f"[api] enqueue_task completed for task_id={task.id}", flush=True)

    # Step 4: Return task information to the client.
    return SubmitTaskResponse(task_id=task.id, status=task.status)


@app.get("/stats", response_model=StatsResponse)
async def get_system_stats() -> StatsResponse:
    """Return basic statistics about tasks in the system.

    The numbers are stored in Redis so that all API instances and workers
    share the same counters:
    - total_tasks_submitted: incremented whenever a task is enqueued.
    - completed_tasks: incremented when a worker completes a task.
    - failed_tasks: incremented when a task reaches max retries and fails.
    - tasks_in_queue: current size of the Redis sorted-set queue.
    """
    raw_stats = await asyncio.to_thread(get_stats)

    status_counts = raw_stats["status_counts"]

    return StatsResponse(
        total_tasks_submitted=sum(status_counts.values()),
        completed_tasks=status_counts["COMPLETED"],
        failed_tasks=status_counts["FAILED"],
        tasks_in_queue=raw_stats["queue_size"],
    )




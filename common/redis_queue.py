import os
import json
import redis
from common.models import Task

# ============================
# Redis Configuration
# ============================

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

QUEUE_KEY = "sentinel:task_queue"
STATUS_KEY = "sentinel:task_status"

client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)


def _log(message: str) -> None:
    print(message, flush=True)

# ============================
# Internal Helpers
# ============================

def _priority_score(priority: int, created_at: float) -> float:
    """
    Calculate score for Redis Sorted Set.
    Higher priority tasks should execute first.
    FIFO order preserved for same priority.
    """
    return -(priority * 1_000_000) + created_at


# ============================
# Queue Operations
# ============================

def enqueue_task(task: Task) -> None:
    """
    Push task into Redis priority queue.
    """
    score = _priority_score(task.priority, task.created_at)
    payload = json.dumps(task.to_dict())

    _log(f"[redis_queue] Enqueue using key={QUEUE_KEY}")
    _log(f"[redis_queue] Enqueue raw payload={payload}")

    try:
        zadd_result = client.zadd(
            QUEUE_KEY,
            {payload: score}
        )
    except Exception as exc:
        _log(f"[redis_queue] Enqueue failed for key={QUEUE_KEY}: {exc}")
        raise

    _log(f"[redis_queue] ZADD result={zadd_result} key={QUEUE_KEY} score={score}")

    task.status = "QUEUED"
    client.hset(STATUS_KEY, task.id, task.status)


def dequeue_task() -> Task | None:
    """
    Pop highest-priority task from queue.
    """
    _log(f"[redis_queue] Dequeue using key={QUEUE_KEY}")
    result = client.zpopmin(QUEUE_KEY, count=1)
    _log(f"[redis_queue] Dequeue raw result={result}")

    if not result:
        return None

    task_json, _ = result[0]
    return Task.from_dict(json.loads(task_json))


def get_queue_size() -> int:
    """
    Number of tasks waiting in queue.
    """
    return client.zcard(QUEUE_KEY)


# ============================
# Task Status Helpers
# ============================

def mark_task_in_progress(task_id: str) -> None:
    client.hset(STATUS_KEY, task_id, "IN_PROGRESS")


def mark_task_completed(task_id: str) -> None:
    client.hset(STATUS_KEY, task_id, "COMPLETED")


def mark_task_failed(task_id: str) -> None:
    client.hset(STATUS_KEY, task_id, "FAILED")


def get_task_status(task_id: str) -> str | None:
    return client.hget(STATUS_KEY, task_id)


def get_all_status_counts() -> dict:
    """
    Count tasks by status.
    """
    statuses = client.hvals(STATUS_KEY)

    counts = {
        "QUEUED": 0,
        "IN_PROGRESS": 0,
        "COMPLETED": 0,
        "FAILED": 0
    }

    for status in statuses:
        if status in counts:
            counts[status] += 1

    return counts


# ============================
# API Helper
# ============================

def get_stats() -> dict:
    """
    Return system-wide statistics.
    Used by /stats endpoint.
    """
    return {
        "queue_size": get_queue_size(),
        "status_counts": get_all_status_counts()
    }


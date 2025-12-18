from __future__ import annotations

import random
import time
from typing import Optional

from common.models import Task
from common.redis_queue import (
    dequeue_task,
    enqueue_task,
    get_queue_size,
    mark_task_completed,
    mark_task_failed,
)


FAILURE_PROBABILITY = 0.2  # 20% of tasks will "fail" to simulate real-world errors
SLEEP_SECONDS = 1.0  # Simulated execution time per task
IDLE_SLEEP_SECONDS = 0.5  # Sleep when there is no work to avoid busy-waiting
MAX_RETRIES = 3  # Maximum number of attempts per task (initial try + 2 more)


def execute_task(task: Task) -> bool:
    """Simulate doing some work for the given task.

    Returns True if the task "succeeds", False if it "fails".
    """
    print(f"[worker] Starting task {task.id} with priority={task.priority}")

    # Simulate actual work taking some time.
    time.sleep(SLEEP_SECONDS)

    # Randomly decide whether the task succeeds or fails.
    if random.random() < FAILURE_PROBABILITY:
        print(f"[worker] Task {task.id} failed during execution.")
        return False

    print(f"[worker] Task {task.id} completed successfully.")
    return True


def worker_loop() -> None:
    """Main worker loop.

    Worker lifecycle:
    1. Connect to the Redis-backed queue through helper functions.
    2. Continuously try to pull the next available task.
    3. If a task is found, simulate execution and decide success/failure.
    4. On failure, apply retry logic with exponential backoff and requeueing.
    5. Update the in-memory task status and log the outcome.
    6. If no task is available, sleep briefly before checking again.

    This simple loop can later be extended with graceful shutdown,
    metrics, and real persistence of task status.
    """
    print("[worker] Starting worker loop. Press Ctrl+C to stop.")
    try:
        while True:
            queue_size = get_queue_size()
            if queue_size == 0:
                # No tasks available; worker idles briefly before polling again.
                time.sleep(IDLE_SLEEP_SECONDS)
                continue

            task: Optional[Task] = dequeue_task()
            if task is None:
                # Another worker may have claimed the task between size check and dequeue.
                time.sleep(IDLE_SLEEP_SECONDS)
                continue

            # Simulate execution of the task.
            success = execute_task(task)

            if success:
                # On success we simply mark the task as completed.
                task.status = "COMPLETED"
                mark_task_completed()
                print(f"[worker] Task {task.id} finished with status={task.status}")
            else:
                # On failure, we increment the retries count and decide whether
                # to give the task another chance or fail it permanently.
                task.retries += 1

                if task.retries > MAX_RETRIES:
                    # The task has exceeded the maximum allowed attempts.
                    # We mark it as permanently failed and do NOT requeue it.
                    task.status = "FAILED"
                    mark_task_failed()
                    print(
                        f"[worker] Task {task.id} reached max retries "
                        f"({MAX_RETRIES}) and is marked as permanently FAILED."
                    )
                else:
                    # The task still has retries left.
                    # We apply exponential backoff before requeueing:
                    #   delay = 2^retries seconds
                    # This means the delay grows as the task fails repeatedly,
                    # giving external systems time to recover.
                    delay = 2**task.retries
                    print(
                        f"[worker] Task {task.id} will be retried "
                        f"(attempt {task.retries}/{MAX_RETRIES}) after {delay}s."
                    )
                    time.sleep(delay)

                    # Requeue the task so that it can be picked up again
                    # by this or another worker.
                    enqueue_task(task)
                    task.status = "REQUEUED"
                    print(f"[worker] Task {task.id} has been requeued for retry.")

    except KeyboardInterrupt:
        # Allow clean exit when running the worker from the command line.
        print("[worker] Received shutdown signal. Exiting worker loop.")


if __name__ == "__main__":
    worker_loop()



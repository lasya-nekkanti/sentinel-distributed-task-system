from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
class Task:
    """Represents a unit of work to be processed by Sentinel workers."""

    id: str  # Unique identifier for this task
    payload: Dict[str, Any]  # Arbitrary data required to execute the task
    priority: int  # Higher value can represent higher priority
    retries: int  # How many times this task has been retried
    status: str  # Current status, e.g. "pending", "running", "completed", "failed"
    created_at: float  # Creation time as a UNIX timestamp (seconds since epoch)

    def to_dict(self) -> Dict[str, Any]:
        """Convert this Task instance to a plain dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Task":
        """Create a Task instance from a dictionary of fields."""
        return Task(
            id=data["id"],
            payload=data.get("payload", {}),
            priority=data.get("priority", 0),
            retries=data.get("retries", 0),
            status=data.get("status", "pending"),
            created_at=data["created_at"],
        )



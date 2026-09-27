"""Thread-safe in-memory task store used by the Task Tracker API."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock


@dataclass
class Task:
    id: int
    title: str
    completed: bool = False


class TaskStore:
    """A tiny CRUD store with deterministic validation for unit testing."""

    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id = 1
        self._lock = Lock()

    def list_tasks(self) -> list[dict]:
        with self._lock:
            return [asdict(self._tasks[key]) for key in sorted(self._tasks)]

    def create_task(self, title: str) -> dict:
        cleaned = self._validate_title(title)
        with self._lock:
            task = Task(id=self._next_id, title=cleaned)
            self._tasks[task.id] = task
            self._next_id += 1
            return asdict(task)

    def get_task(self, task_id: int) -> dict:
        with self._lock:
            return asdict(self._require(task_id))

    def update_task(self, task_id: int, *, title=None, completed=None) -> dict:
        with self._lock:
            task = self._require(task_id)
            if title is not None:
                task.title = self._validate_title(title)
            if completed is not None:
                if not isinstance(completed, bool):
                    raise ValueError("completed must be true or false")
                task.completed = completed
            return asdict(task)

    def delete_task(self, task_id: int) -> dict:
        with self._lock:
            task = self._require(task_id)
            del self._tasks[task_id]
            return asdict(task)

    def count(self) -> int:
        with self._lock:
            return len(self._tasks)

    @staticmethod
    def _validate_title(title: str) -> str:
        if not isinstance(title, str):
            raise TypeError("title must be a string")
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("title must not be empty")
        if len(cleaned) > 120:
            raise ValueError("title must be 120 characters or fewer")
        return cleaned

    def _require(self, task_id: int) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"task {task_id} not found") from exc

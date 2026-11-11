from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Status(Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Task:
    id: int
    title: str
    priority: Priority = Priority.MEDIUM
    status: Status = Status.TODO
    tags: list[str] = field(default_factory=list)
    assignee: Optional[str] = None


class TaskManager:
    def __init__(self) -> None:
        self.tasks: dict[int, Task] = {}
        self.next_id = 1

    def add(self, title: str, priority: Priority = Priority.MEDIUM, tags: Optional[list[str]] = None) -> Task:
        t = Task(self.next_id, title, priority, tags=tags if tags is not None else [])
        self.tasks[t.id] = t
        self.next_id += 1
        return t

    def move(self, task_id: int, status: Status) -> None:
        if task_id not in self.tasks:
            raise KeyError(f"no task {task_id}")
        t = self.tasks[task_id]
        if t.status == Status.DONE and status != Status.DONE:
            raise ValueError("cannot reopen a finished task")
        t.status = status

    def by_status(self, status: Status) -> list[Task]:
        return sorted((t for t in self.tasks.values() if t.status == status), key=lambda t: (-t.priority.value, t.id))

    def assign(self, task_id: int, who: str) -> None:
        self.tasks[task_id].assignee = who

    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in self.tasks.values():
            out[t.status.value] = out.get(t.status.value, 0) + 1
        return out

    def tagged(self, tag: str) -> list[int]:
        return [t.id for t in self.tasks.values() if tag in t.tags]


def main() -> None:
    m = TaskManager()
    m.add("write docs", Priority.LOW, ["docs"])
    m.add("fix bug", Priority.HIGH, ["code", "urgent"])
    m.add("review PR", tags=["code"])
    m.add("deploy", Priority.HIGH)
    m.move(2, Status.DOING)
    m.move(4, Status.DONE)
    m.assign(2, "ann")
    print([t.title for t in m.by_status(Status.TODO)], [t.title for t in m.by_status(Status.DOING)])
    print(m.summary(), m.tagged("code"), m.tasks[2])
    for tid, st in ((9, Status.DONE), (4, Status.TODO)):
        try:
            m.move(tid, st)
        except KeyError as e:
            print("missing:", e)
        except ValueError as e:
            print("invalid:", e)
    print(sorted(p.name for p in Priority), [s.value for s in Status], Priority(3).name, Status("done").value)
    print(m.tasks[1].priority == Priority.LOW, m.tasks[3].assignee is None, m.tasks[2].assignee)


if __name__ == "__main__":
    main()

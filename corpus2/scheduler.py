import heapq
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Task:
    name: str
    priority: int
    duration: int
    deps: list[str] = field(default_factory=list)


class Scheduler:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}
        self.done: set[str] = set()
        self.clock = 0
        self.log: list[str] = []

    def add(self, task: Task) -> None:
        if task.name in self.tasks:
            raise ValueError(f"duplicate task {task.name}")
        self.tasks[task.name] = task

    def ready(self) -> list[Task]:
        return [t for t in self.tasks.values() if t.name not in self.done and all(d in self.done for d in t.deps)]

    def run(self) -> int:
        while len(self.done) < len(self.tasks):
            heap: list[tuple[int, str]] = []
            for t in self.ready():
                heapq.heappush(heap, (-t.priority, t.name))
            if not heap:
                raise RuntimeError("deadlock")
            _, name = heapq.heappop(heap)
            task = self.tasks[name]
            self.clock += task.duration
            self.done.add(name)
            self.log.append(f"{self.clock:>3} {name}")
        return self.clock


def round_robin(jobs: list[tuple[str, int]], quantum: int) -> list[str]:
    q = deque(jobs)
    order: list[str] = []
    t = 0
    while q:
        name, remaining = q.popleft()
        run = min(quantum, remaining)
        t += run
        if remaining > run:
            q.append((name, remaining - run))
        else:
            order.append(f"{name}@{t}")
    return order


def main() -> None:
    s = Scheduler()
    s.add(Task("compile", 5, 4))
    s.add(Task("test", 3, 6, ["compile"]))
    s.add(Task("lint", 9, 1))
    s.add(Task("package", 4, 2, ["test", "lint"]))
    s.add(Task("docs", 1, 3, ["compile"]))
    print(s.run())
    for line in s.log:
        print(line)
    try:
        s.add(Task("docs", 1, 1))
    except ValueError as e:
        print(e)
    bad = Scheduler()
    bad.add(Task("a", 1, 1, ["b"]))
    bad.add(Task("b", 1, 1, ["a"]))
    try:
        bad.run()
    except RuntimeError as e:
        print("failed:", e)
    print(round_robin([("A", 5), ("B", 2), ("C", 7)], 3))
    print(Task("x", 1, 2), Task("x", 1, 2) == Task("x", 1, 2))


if __name__ == "__main__":
    main()

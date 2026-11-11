import heapq
from dataclasses import dataclass
from typing import NamedTuple


@dataclass(order=True)
class Version:
    major: int
    minor: int = 0
    tag: str = ""


@dataclass
class Item:
    name: str
    qty: int

    def __post_init__(self) -> None:
        self.name = self.name.strip().title()


class Point(NamedTuple):
    x: int
    y: int

    def dist2(self) -> int:
        return self.x * self.x + self.y * self.y


class Job:
    def __init__(self, prio: int, name: str) -> None:
        self.prio = prio
        self.name = name

    def __lt__(self, other: "Job") -> bool:
        return self.prio < other.prio

    def __repr__(self) -> str:
        return f"Job({self.prio}, {self.name})"


class Node:
    def __init__(self, v: int) -> None:
        self.v = v


def main() -> None:
    vs = [Version(1, 2), Version(1, 0, "b"), Version(0, 9), Version(1, 0, "a")]
    print(sorted(vs), max(vs), min(vs), Version(1) < Version(2), Version(2, 1) >= Version(2, 1), vs[0] > vs[1])
    print(Item("  widget ", 3), Item("x", 1) == Item("x", 1))
    p = Point(3, 4)
    a, b = p
    print(p, p.x + p.y, a, b, p.dist2(), Point(1, 2) == Point(1, 2), sorted([Point(2, 1), Point(1, 5)]))
    jobs = [Job(3, "c"), Job(1, "a"), Job(2, "b")]
    print(sorted(jobs), min(jobs), max(jobs))
    jobs.sort()
    heap: list[Job] = []
    for j in [Job(5, "e"), Job(2, "x"), Job(9, "z"), Job(1, "q")]:
        heapq.heappush(heap, j)
    print(jobs, [heapq.heappop(heap) for _ in range(3)], jobs[0] < jobs[1], jobs[1] > jobs[0])
    n1, n2 = Node(1), Node(2)
    seen = {n1, n2}
    seen.add(n1)
    owners: dict[Node, str] = {n1: "one"}
    owners[n2] = "two"
    print(len(seen), n1 in seen, Node(3) in seen, owners[n2], len(owners))


if __name__ == "__main__":
    main()

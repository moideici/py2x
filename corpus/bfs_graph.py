from collections import deque
from typing import Optional


def build_graph(edges: list[tuple[str, str]]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)
    return graph


def shortest_path(graph: dict[str, list[str]], start: str, goal: str) -> Optional[list[str]]:
    parent: dict[str, Optional[str]] = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == goal:
            path = []
            cur: Optional[str] = node
            while cur is not None:
                path.append(cur)
                cur = parent[cur]
            return path[::-1]
        for nxt in graph.get(node, []):
            if nxt not in parent:
                parent[nxt] = node
                queue.append(nxt)
    return None


def components(graph: dict[str, list[str]]) -> int:
    seen: set[str] = set()
    count = 0
    for node in graph:
        if node in seen:
            continue
        count += 1
        stack = [node]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(graph[cur])
    return count


def main() -> None:
    edges = [("a", "b"), ("b", "c"), ("c", "d"), ("a", "e"), ("e", "d"), ("x", "y")]
    g = build_graph(edges)
    print(shortest_path(g, "a", "d"))
    print(shortest_path(g, "a", "y"))
    print("components:", components(g))


if __name__ == "__main__":
    main()

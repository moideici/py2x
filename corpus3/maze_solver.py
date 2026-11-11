from collections import deque
from typing import Optional

Grid = list[str]
Pos = tuple[int, int]

MAZE: Grid = [
    "S.#.......",
    ".##.####..",
    "....#..#..",
    ".####.##.#",
    "......#..E",
]


def find(grid: Grid, ch: str) -> Optional[Pos]:
    for r, row in enumerate(grid):
        c = row.find(ch)
        if c != -1:
            return (r, c)
    return None


def neighbors(grid: Grid, p: Pos) -> list[Pos]:
    r, c = p
    out: list[Pos] = []
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < len(grid) and 0 <= nc < len(grid[0]) and grid[nr][nc] != "#":
            out.append((nr, nc))
    return out


def bfs(grid: Grid, start: Pos, goal: Pos) -> Optional[list[Pos]]:
    prev: dict[Pos, Optional[Pos]] = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            path: list[Pos] = []
            node: Optional[Pos] = cur
            while node is not None:
                path.append(node)
                node = prev[node]
            return path[::-1]
        for nxt in neighbors(grid, cur):
            if nxt not in prev:
                prev[nxt] = cur
                q.append(nxt)
    return None


def count_reachable(grid: Grid, start: Pos) -> int:
    seen = {start}
    stack = [start]
    while stack:
        cur = stack.pop()
        for nxt in neighbors(grid, cur):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen)


def render(grid: Grid, path: list[Pos]) -> list[str]:
    cells = [list(row) for row in grid]
    for r, c in path[1:-1]:
        cells[r][c] = "*"
    return ["".join(row) for row in cells]


def main() -> None:
    s, e = find(MAZE, "S"), find(MAZE, "E")
    print(s, e, find(MAZE, "X"))
    if s is None or e is None:
        return
    path = bfs(MAZE, s, e)
    if path is None:
        print("no path")
        return
    print(len(path) - 1, path[:4], path[-1])
    for line in render(MAZE, path):
        print(line)
    print(count_reachable(MAZE, s), count_reachable(MAZE, (0, 3)))
    blocked = [row.replace(".", "#") if i == 2 else row for i, row in enumerate(MAZE)]
    print(bfs(blocked, s, e) is None)


if __name__ == "__main__":
    main()

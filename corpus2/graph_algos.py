from collections import defaultdict, deque


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n
        self.components = n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        self.components -= 1
        return True


def kruskal(n: int, edges: list[tuple[int, int, int]]) -> tuple[int, list[tuple[int, int, int]]]:
    uf = UnionFind(n)
    total = 0
    used: list[tuple[int, int, int]] = []
    for w, a, b in sorted(edges):
        if uf.union(a, b):
            total += w
            used.append((w, a, b))
    return total, used


def topo_sort(n: int, deps: list[tuple[int, int]]) -> list[int]:
    graph: defaultdict[int, list[int]] = defaultdict(list)
    indeg = [0] * n
    for a, b in deps:
        graph[a].append(b)
        indeg[b] += 1
    queue = deque(i for i in range(n) if indeg[i] == 0)
    order: list[int] = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for v in graph[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    if len(order) != n:
        raise ValueError("cycle detected")
    return order


def components(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    adj: dict[int, list[int]] = {i: [] for i in range(n)}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen: set[int] = set()
    result: list[list[int]] = []
    for s in range(n):
        if s in seen:
            continue
        comp: list[int] = []
        stack = [s]
        seen.add(s)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        result.append(sorted(comp))
    return result


def main() -> None:
    edges = [(4, 0, 1), (8, 0, 2), (2, 1, 2), (6, 1, 3), (3, 2, 3), (9, 3, 4), (1, 2, 4)]
    total, used = kruskal(5, edges)
    print(total, used)
    print(topo_sort(6, [(5, 2), (5, 0), (4, 0), (4, 1), (2, 3), (3, 1)]))
    try:
        topo_sort(3, [(0, 1), (1, 2), (2, 0)])
    except ValueError as e:
        print("error:", e)
    print(components(7, [(0, 1), (1, 2), (3, 4), (5, 5)]))
    uf = UnionFind(6)
    print([uf.union(a, b) for a, b in [(0, 1), (1, 2), (0, 2), (3, 4)]], uf.components)


if __name__ == "__main__":
    main()

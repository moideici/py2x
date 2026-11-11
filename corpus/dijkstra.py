import heapq
import math


def dijkstra(graph: dict[int, list[tuple[int, float]]], source: int, n: int) -> list[float]:
    dist = [math.inf] * n
    dist[source] = 0.0
    heap: list[tuple[float, int]] = [(0.0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in graph.get(u, []):
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist


def main() -> None:
    graph = {
        0: [(1, 4.0), (2, 1.0)],
        2: [(1, 2.0), (3, 7.5)],
        1: [(3, 1.0)],
        3: [(4, 3.0)],
    }
    dist = dijkstra(graph, 0, 6)
    for i, d in enumerate(dist):
        label = "unreachable" if d == math.inf else f"{d:.1f}"
        print(f"node {i}: {label}")


if __name__ == "__main__":
    main()

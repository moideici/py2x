import heapq
from collections import Counter, OrderedDict, defaultdict, deque


def bfs(graph: dict[int, list[int]], start: int) -> list[int]:
    seen = {start}
    order: list[int] = []
    q = deque([start])
    while q:
        node = q.popleft()
        order.append(node)
        for nxt in graph[node]:
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return order


def dijkstra(adj: dict[int, list[tuple[int, int]]], src: int) -> dict[int, int]:
    dist: dict[int, int] = {src: 0}
    heap = [(0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist


def main() -> None:
    g = {1: [2, 3], 2: [4], 3: [4, 5], 4: [6], 5: [6], 6: []}
    print(bfs(g, 1))

    adj = {1: [(2, 7), (3, 9), (6, 14)], 2: [(1, 7), (3, 10), (4, 15)], 3: [(1, 9), (2, 10), (4, 11), (6, 2)],
           4: [(2, 15), (3, 11), (5, 6)], 5: [(4, 6), (6, 9)], 6: [(1, 14), (3, 2), (5, 9)]}
    print(dijkstra(adj, 1))

    words = "the quick brown fox jumps over the lazy dog the end".split()
    c = Counter(words)
    print(c.most_common(2), c["the"], c["zzz"], len(c))
    print(c)
    c.update(["fox", "fox"])
    print(c["fox"], sum(c.values()))

    groups: defaultdict[int, list[str]] = defaultdict(list)
    for w in words:
        groups[len(w)].append(w)
    print(groups)
    print(sorted(groups.keys()))

    counts = defaultdict(int)
    for ch in "mississippi":
        counts[ch] += 1
    print(dict(counts) == {"m": 1, "i": 4, "s": 4, "p": 2}, counts["i"], "z" in counts)

    od: OrderedDict[str, int] = OrderedDict()
    od["a"] = 1
    od["b"] = 2
    od["c"] = 3
    od.move_to_end("a")
    print(od, od.popitem(last=False))

    s = {3, 1, 2, 10, 33, 17}
    t = {2, 3, 4, 5}
    print(s, t, s | t, s & t, s - t, s ^ t)
    print(1 in s, 99 in s, len(s), s <= t, {1, 2} <= s)
    s.add(100)
    s.discard(3)
    print(sorted(s), min(s), max(s), sum(s))
    u = set()
    for i in range(20):
        u.add(i * 7 % 13)
    print(u, len(u))
    names = {"bob", "alice", "carol"}
    print(sorted(names), "bob" in names)
    sq = {x * x for x in range(6)}
    print(sq)

    d = deque([1, 2, 3], maxlen=4)
    d.append(4)
    d.append(5)
    d.appendleft(0)
    print(d, d[0], d[-1], len(d), 3 in d)
    d.rotate(1)
    print(d, d.pop(), d.popleft(), list(d))

    h = [5, 3, 8, 1, 9, 2]
    heapq.heapify(h)
    print(h)
    heapq.heappush(h, 0)
    print([heapq.heappop(h) for _ in range(3)], h)
    print(heapq.nlargest(2, [4, 1, 7, 3]), heapq.nsmallest(2, [4, 1, 7, 3]))


if __name__ == "__main__":
    main()

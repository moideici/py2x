class Basket:
    def __init__(self) -> None:
        self.items = []
        self.prices = {}

    def add(self, name: str, price: float) -> None:
        self.items.append(name)
        self.prices[name] = price

    def total(self) -> float:
        t = 0.0
        for name in self.items:
            t += self.prices[name]
        return t


def evens_doubled(xs: list[int]) -> list[int]:
    out = []
    for x in xs:
        if x % 2 == 0:
            out.append(x * 2)
    return out


def histogram(words: list[str]) -> dict[str, int]:
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return counts


def pairs_sum(xs: list[int]) -> list[tuple[int, int]]:
    result = list()
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            result.append((xs[i], xs[j]))
    return result


def group_by_len(words: list[str]) -> dict[int, list[str]]:
    groups = dict()
    for w in words:
        if len(w) not in groups:
            groups[len(w)] = []
        groups[len(w)].append(w)
    return groups


def flatten(nested: list[list[int]]) -> list[int]:
    flat = []
    for row in nested:
        for v in row:
            flat.append(v)
    return flat


def main() -> None:
    b = Basket()
    b.add("pen", 1.5)
    b.add("book", 12.0)
    print(b.items, b.prices, b.total())
    print(evens_doubled([1, 2, 3, 4, 5, 6]))
    print(histogram(["a", "b", "a", "c", "a", "b"]))
    print(pairs_sum([1, 2, 3]))
    print(group_by_len(["a", "bb", "cc", "d", "eee"]))
    print(flatten([[1, 2], [], [3]]))
    names = []
    scores = {}
    for i, n in enumerate(["x", "y", "z"]):
        names.append(n)
        scores[n] = i * 10
    print(names, scores)
    matrix = []
    for r in range(3):
        row = []
        for c in range(3):
            row.append(r * c)
        matrix.append(row)
    print(matrix)


if __name__ == "__main__":
    main()

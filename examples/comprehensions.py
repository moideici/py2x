def squares(n: int) -> list[int]:
    return [i * i for i in range(n)]


def evens(xs: list[int]) -> list[int]:
    return [x for x in xs if x % 2 == 0]


def pairs(n: int) -> list[tuple[int, int]]:
    return [(i, j) for i in range(n) for j in range(i) if (i + j) % 2 == 1]


def matrix(n: int, m: int) -> list[list[int]]:
    return [[i * m + j for j in range(m)] for i in range(n)]


def main() -> None:
    print(squares(6), evens([1, 2, 3, 4, 5, 6]))
    print(pairs(4))
    grid = matrix(3, 4)
    print(grid, [row[0] for row in grid])
    words = ["apple", "kiwi", "fig", "banana"]
    lens = {w: len(w) for w in words}
    print(lens, sum(len(w) for w in words), max(len(w) for w in words))
    flags = [v > 2 for v in [1, 2, 3, 4]]
    print(flags, any(flags), all(flags), any(v > 3 for v in [1, 2, 4]), all(v > 0 for v in [1, 2]))
    print([0] * 5, [1, 2] * 3, "ab" * 3, "-" * 10, 3 * [7])
    print([1, 2] + [3], sorted([3, 1, 2]) + [0])
    for i, w in enumerate(words):
        print(i, w)
    for i, w in enumerate(words, 1):
        print(i, w)
    for a, b in zip([1, 2, 3], ["x", "y"]):
        print(a, b)
    for wd in reversed(words):
        print(wd)
    print(list(enumerate(["a", "b"])), list(zip([1, 2], [3, 4])), list(reversed([1, 2, 3])))
    xs = [5, 3, 8]
    print(xs.pop(), xs.pop(0), xs)
    xs.extend([1, 2])
    xs.insert(1, 99)
    xs.insert(-1, 7)
    xs.insert(100, 8)
    print(xs, xs.index(99), xs.count(1), xs.count(5))
    xs.remove(99)
    print(xs)
    nested = [[j for j in range(i)] for i in range(4)]
    print(nested, sum(sum(r) for r in nested))
    table = {k: [k * j for j in range(3)] for k in range(3)}
    print(table)
    inv = {v: k for k, v in lens.items()}
    print(inv)
    k = 10
    print([k + v for v in range(3)], k)
    x = 100
    print([x for x in range(3)], x)


if __name__ == "__main__":
    main()

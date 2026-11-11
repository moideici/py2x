def divmod2(a: int, b: int) -> tuple[int, int]:
    return a // b, a % b


def min_max(xs: list[int]) -> tuple[int, int]:
    lo: int = xs[0]
    hi: int = xs[0]
    for x in xs:
        if x < lo:
            lo = x
        if x > hi:
            hi = x
    return lo, hi


def swap(p: tuple[str, int]) -> tuple[int, str]:
    return p[1], p[0]


def main() -> None:
    q, r = divmod2(-17, 5)
    print(q, r)
    t: tuple[int, int] = divmod2(17, 5)
    print(t, t[0], t[1], t[-1])
    lo, hi = min_max([4, -2, 9, 0])
    print(lo, hi)
    print(swap(("x", 3)))

    pairs: list[tuple[str, int]] = [("b", 2), ("a", 9), ("c", 1)]
    pairs.sort()
    print(pairs)
    for name, score in pairs:
        print(name, score)
    print(sorted([(2, "x"), (1, "z"), (1, "y")]))
    print(("a", 1) in pairs, ("a", 2) in pairs)

    ages: dict[str, int] = {"zoe": 31, "adam": 25}
    ages["bob"] = 40
    ages["zoe"] += 1
    for k, v in ages.items():
        print(k, v)
    print(list(ages.keys()), list(ages.values()), len(ages.items()))
    print(sum(ages.values()), max(ages.values()), sorted(ages.keys()))
    print(ages)

    grid: dict[tuple[int, int], str] = {}
    grid[(0, 1)] = "a"
    grid[(1, 0)] = "b"
    grid[(0, 1)] = "c"
    print(grid[(0, 1)], len(grid), (1, 0) in grid, (5, 5) in grid)
    print(grid)

    (a, b), c = (1, 2), 3
    print(a, b, c)
    a, b = b, a
    print(a, b)
    print((1, 2) == (1, 2), (1, 2) < (1, 3), (1, "a") != (1, "b"), (2, 0) > (1, 9))
    one: tuple[int] = (5,)
    print(one, (1.5, True, "s"), ((1, 2), 3))
    total: float = 0.0
    for i, w in [(1, 0.5), (2, 1.5)]:
        total += i * w
    print(total)


if __name__ == "__main__":
    main()

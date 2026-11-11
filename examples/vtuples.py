def total(*nums: int) -> int:
    return sum(nums)


def describe(label: str, *parts: str) -> str:
    return label + ":" + ",".join(parts) + f"({len(parts)})"


def main() -> None:
    m = [[1, 2, 3], [4, 5, 6]]
    cols = list(zip(*m))
    print(cols, cols[0], len(cols))
    print([sum(c) for c in zip(*m)], [list(r) for r in zip(*m)])
    t = tuple([3, 1, 2])
    print(t, sorted(t), max(t), t[0], 2 in t, len(t), tuple("ab"))
    print(total(), total(1), total(1, 2, 3), describe("x"), describe("y", "a", "b"))
    xs = [4, 5, 6]
    print(total(*xs), describe("z", *["p", "q"]))
    print(*xs)
    print(*xs, sep=", ")
    print(*[1.5, 2.5], sep=" | ", end="!\n")
    for n in (7, 9, 11):
        for i in range(2, n):
            if n % i == 0:
                print(n, "composite")
                break
        else:
            print(n, "prime")
    k = 0
    while k < 3:
        k += 1
    else:
        print("while done", k)
    first, *rest = [1, 2, 3, 4]
    *init, last = xs
    a, *mid, z = [10, 20, 30, 40]
    print(first, rest, init, last, a, mid, z)
    seen = {tuple([1, 2]): "a"}
    print(seen[tuple([1, 2])], seen)


if __name__ == "__main__":
    main()

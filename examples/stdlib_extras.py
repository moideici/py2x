import bisect
import itertools
import math
from functools import lru_cache
from itertools import accumulate, chain, combinations, islice, pairwise, permutations, product
from typing import ClassVar


@lru_cache(maxsize=None)
def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)


@lru_cache(None)
def paths(r: int, c: int) -> int:
    if r == 0 or c == 0:
        return 1
    return paths(r - 1, c) + paths(r, c - 1)


class Config:
    DEBUG: ClassVar[bool] = False
    names: ClassVar[list[str]] = []


def main() -> None:
    print(fib(80), paths(10, 10))
    xs = [1, 3, 3, 5, 8]
    print(bisect.bisect_left(xs, 3), bisect.bisect_right(xs, 3), bisect.bisect(xs, 9))
    bisect.insort(xs, 4)
    bisect.insort_left(xs, 3)
    print(xs)
    print(list(product([1, 2], "ab")), list(product([0, 1], repeat=3))[:3])
    print(list(permutations([1, 2, 3])), list(permutations("abc", 2))[:4])
    print(list(combinations([1, 2, 3, 4], 2)), len(list(itertools.combinations_with_replacement("abc", 2))))
    print(list(accumulate([1, 2, 3, 4])), list(accumulate([1, 2, 3, 4], lambda a, b: a * b)), list(accumulate([3, 1, 4], max, initial=0)))
    print(list(chain([1, 2], (3,), [4, 5])), list(chain.from_iterable([[1], [2, 3]])), list(islice(range(10), 2, 5)), list(pairwise([1, 4, 9, 16])))
    for a, b in combinations(["x", "y", "z"], 2):
        print(a + b, end=" ")
    print()
    n = 4
    print(len(list(permutations(range(n)))), sum(len(c) for c in combinations(range(5), 3)), [sum(p) for p in permutations([1, 2], 2)])
    print(math.comb(10, 3), math.perm(5, 2), math.prod([1, 2, 3, 4]), math.prod([0.5, 4.0]), math.isclose(0.1 + 0.2, 0.3), math.copysign(2.0, -1.0))
    try:
        math.sqrt(-1.0)
    except ValueError as e:
        print("domain:", e)
    try:
        print(math.log(0.0))
    except ValueError as e:
        print("domain:", e)
    try:
        print(2.0 ** 5000)
    except OverflowError as e:
        print("overflow:", e)
    try:
        print(0.0 ** -1.0)
    except ZeroDivisionError as e:
        print("zero:", e)
    d1 = {"x": 1, "y": 2}
    d2 = {"y": 20, "z": 30}
    print(d1 | d2, {**d1, **d2, "w": 0}, [*xs[:2], 99, *xs[3:]], dict.fromkeys(["p", "q"], 0))
    print("key=value=x".partition("="), "a.b.c".rpartition("."), "abc".isascii(), "x1".isidentifier(), "hello".rindex("l"))
    try:
        try:
            int("zz")
        except ValueError as e:
            raise RuntimeError("wrapped") from e
    except RuntimeError as e:
        print("got", e)
    Config.names.append("n1")
    print(Config.DEBUG, Config.names)


if __name__ == "__main__":
    main()

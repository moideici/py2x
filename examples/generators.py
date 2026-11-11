from itertools import islice
from typing import Iterable, Iterator


def countdown(n: int) -> Iterator[int]:
    while n > 0:
        yield n
        n -= 1


def fib() -> Iterator[int]:
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


def evens(limit: int) -> Iterator[int]:
    for i in range(limit):
        if i % 2 == 0:
            yield i
        if i > 100:
            return


def chunks(xs: list[int], size: int) -> Iterator[list[int]]:
    for i in range(0, len(xs), size):
        yield xs[i:i + size]


def flatten(nested: list[list[int]]) -> Iterator[int]:
    for row in nested:
        yield from row


def words(text: str) -> Iterator[str]:
    for w in text.split():
        yield w.upper()


def total(it: Iterable[int]) -> int:
    t = 0
    for x in it:
        t += x
    return t


class Tree:
    def __init__(self, v: int, kids: list["Tree"]) -> None:
        self.v = v
        self.kids = kids

    def walk(self) -> Iterator[int]:
        yield self.v
        for k in self.kids:
            yield from k.walk()


def main() -> None:
    print(list(countdown(5)), sum(countdown(100)), max(evens(9)))
    for x in countdown(3):
        print("tick", x)
    g = fib()
    print(next(g), next(g), next(g), next(g), next(g))
    print(list(islice(fib(), 12)), next(fib(), -1))
    for i, f in zip(range(1, 6), fib()):
        print(i, f, end="; ")
    print()
    big = 0
    for f in fib():
        if f > 1000:
            big = f
            break
    print(big, list(chunks([1, 2, 3, 4, 5, 6, 7], 3)), list(flatten([[1, 2], [], [3]])))
    print(list(words("hello big world")), total(countdown(4)), sorted(evens(7), reverse=True))
    t = Tree(1, [Tree(2, [Tree(4, [])]), Tree(3, [])])
    print(list(t.walk()), sum(t.walk()))
    e = countdown(2)
    print(next(e), next(e), next(e, 99))
    try:
        next(e)
    except StopIteration:
        print("exhausted")


if __name__ == "__main__":
    main()

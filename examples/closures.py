from typing import Callable


def make_counter() -> Callable[[], int]:
    count = 0

    def inc() -> int:
        nonlocal count
        count += 1
        return count

    return inc


def make_multiplier(k: int) -> Callable[[int], int]:
    def mul(x: int) -> int:
        return x * k

    return mul


def apply_n(f: Callable[[int], int], n: int, x: int) -> int:
    for _ in range(n):
        x = f(x)
    return x


def outer(xs: list[int]) -> int:
    total = 0

    def add(v: int) -> None:
        nonlocal total
        total += v

    for x in xs:
        add(x)

    def fact(n: int) -> int:
        return 1 if n <= 1 else n * fact(n - 1)

    return total + fact(5)


def main() -> None:
    c1, c2 = make_counter(), make_counter()
    print(c1(), c1(), c1(), c2())
    triple = make_multiplier(3)
    print(triple(7), apply_n(triple, 3, 2), apply_n(make_multiplier(2), 10, 1))
    print(outer([1, 2, 3]))


if __name__ == "__main__":
    main()

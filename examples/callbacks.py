from functools import reduce
from typing import Callable


def apply_twice(f: Callable[[int], int], x: int) -> int:
    return f(f(x))


def compose(f: Callable[[int], int], g: Callable[[int], int]) -> Callable[[int], int]:
    return lambda x: f(g(x))


def make_adder(n: int) -> Callable[[int], int]:
    return lambda x: x + n


def square(x: int) -> int:
    return x * x


def apply_all(fs: list[Callable[[float], float]], x: float) -> list[float]:
    return [f(x) for f in fs]


class Button:
    def __init__(self, label: str) -> None:
        self.label = label
        self.handler: Callable[[str], str] = lambda s: "default:" + s
        self.clicks = 0

    def click(self) -> str:
        self.clicks += 1
        return self.handler(self.label)


def main() -> None:
    print(apply_twice(square, 3), apply_twice(lambda v: v + 10, 1))
    add5 = make_adder(5)
    inc_then_square = compose(square, add5)
    print(add5(1), inc_then_square(2), compose(add5, square)(3))
    ops: dict[str, Callable[[int, int], int]] = {
        "add": lambda a, b: a + b,
        "mul": lambda a, b: a * b,
        "pow": lambda a, b: a ** b,
    }
    for name in sorted(ops):
        print(name, ops[name](3, 4))
    xs = [1, 2, 3, 4, 5, 6]
    print(list(map(square, xs)), list(map(lambda v: v * 2, xs)), list(filter(lambda v: v % 2 == 0, xs)))
    print(sum(map(lambda v: v * v, filter(lambda v: v > 2, xs))), list(map(str, xs)), list(map(lambda a, b: a + b, xs, xs[::-1])))
    print(reduce(lambda a, b: a + b, xs), reduce(lambda a, b: a * b, xs, 1), reduce(max, xs) if False else reduce(lambda a, b: a if a > b else b, xs))
    print(apply_all([lambda v: v + 0.5, lambda v: v * 2.0, abs], -3.0) if False else apply_all([lambda v: v + 0.5, lambda v: v * 2.0], -3.0))
    b = Button("ok")
    print(b.click(), b.clicks)
    b.handler = lambda s: s.upper() + "!"
    print(b.click(), b.clicks)
    print(", ".join(map(str, sorted(xs, key=lambda v: -v))))
    scale: Callable[[float], float] = lambda v: v * 1.5
    print(scale(2.0), [scale(v) for v in [1.0, 2.0]])


if __name__ == "__main__":
    main()

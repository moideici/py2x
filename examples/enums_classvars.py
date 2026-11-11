from enum import Enum, auto


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

    def is_warm(self) -> bool:
        return self is Color.RED

    def describe(self) -> str:
        return f"{self.name.lower()}={self.value}"


class Level(Enum):
    LOW = "low"
    HIGH = "high"


class Dir(Enum):
    N = auto()
    E = auto()
    S = auto()
    W = auto()


class Counter:
    total = 0
    LIMIT: int = 3
    names: list[str] = []

    def __init__(self, label: str) -> None:
        self.label = label
        Counter.total += 1
        Counter.names.append(label)

    def over(self) -> bool:
        return Counter.total > self.LIMIT


def turn_right(d: Dir) -> Dir:
    order = [Dir.N, Dir.E, Dir.S, Dir.W]
    return order[(order.index(d) + 1) % 4]


def main() -> None:
    print(Color.RED, Color.GREEN.value, Color.BLUE.name, repr(Color.RED), Color(2), Level("high"))
    print([c.name for c in Color], list(Level), len(Color), Color.RED == Color.RED, Color.RED is Color.BLUE)
    print(Color.RED.is_warm(), Color.GREEN.is_warm(), Color.BLUE.describe())
    count: dict[Color, int] = {}
    for c in [Color.RED, Color.BLUE, Color.RED, Color.GREEN, Color.RED]:
        count[c] = count.get(c, 0) + 1
    print({k.name: v for k, v in count.items()}, count[Color.RED])
    print(turn_right(Dir.W), turn_right(Dir.N), Dir.S.value)
    try:
        Color(9)
    except ValueError as e:
        print("error:", e)
    a, b, c, d = Counter("a"), Counter("b"), Counter("c"), Counter("d")
    print(Counter.total, Counter.names, a.over(), Counter.LIMIT)
    Counter.total = 0
    print(Counter.total, d.label)


if __name__ == "__main__":
    main()

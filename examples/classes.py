from dataclasses import dataclass, field


@dataclass
class Point:
    x: int
    y: int = 0

    def dist2(self) -> int:
        return self.x * self.x + self.y * self.y

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy


@dataclass(frozen=True)
class Money:
    amount: int
    currency: str = "EUR"

    def double(self) -> "Money":
        return Money(self.amount * 2, self.currency)


@dataclass
class Team:
    name: str
    members: list[str] = field(default_factory=list)
    score: float = 0.0

    def add(self, who: str) -> "Team":
        self.members.append(who)
        return self


class Account:
    def __init__(self, owner: str, balance: int = 0) -> None:
        self.owner = owner
        self.balance = balance
        self.history: list[int] = []

    def deposit(self, amount: int) -> None:
        self.balance += amount
        self.history.append(amount)

    def withdraw(self, amount: int) -> bool:
        if amount > self.balance:
            return False
        self.balance -= amount
        self.history.append(-amount)
        return True

    def __str__(self) -> str:
        return f"{self.owner}: {self.balance}"


class Counter:
    def __init__(self) -> None:
        self.n: int = 0

    def inc(self) -> "Counter":
        self.n += 1
        return self


def bump(p: Point) -> None:
    p.x += 100


def main() -> None:
    p = Point(3, 4)
    q = Point(x=3, y=4)
    print(p, q, p == q, p.dist2())
    r = p
    r.move(1, 1)
    print(p, r, p == r)
    bump(p)
    print(p.x, q.x)

    pts: list[Point] = [Point(1), Point(2, 3)]
    pts.append(Point(y=9, x=7))
    print(pts, len(pts))
    print(Point(1) in pts, Point(5, 5) in pts)
    pts[0].move(10, 10)
    print(pts[0])

    m = Money(5)
    print(m, m.double(), m == Money(5, "EUR"), m.double().amount)

    t = Team("red")
    t.add("ann").add("bob")
    print(t, len(t.members))
    t2 = Team("blue", ["z"], 2.5)
    print(t2)

    acc = Account("zoe", 10)
    acc.deposit(5)
    print(acc.withdraw(100), acc.withdraw(3), acc)
    print(acc.history, acc.balance)

    c = Counter()
    c.inc().inc().inc()
    print(c.n)

    book: dict[str, Point] = {}
    book["a"] = Point(1, 2)
    book["a"].x = 50
    print(book["a"], len(book))
    for name, pt in book.items():
        print(name, pt.dist2())
    pair: tuple[Point, int] = (Point(0, 1), 5)
    print(pair)


if __name__ == "__main__":
    main()

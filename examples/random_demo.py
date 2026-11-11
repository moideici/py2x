import random
from random import randint, shuffle


def monte_carlo_pi(n: int) -> float:
    inside = 0
    for _ in range(n):
        x, y = random.random(), random.random()
        if x * x + y * y <= 1.0:
            inside += 1
    return 4.0 * inside / n


class Dice:
    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed)
        self.rolls: list[int] = []

    def roll(self) -> int:
        v = self.rng.randint(1, 6)
        self.rolls.append(v)
        return v


def main() -> None:
    random.seed(42)
    print([random.random() for _ in range(3)])
    print([random.randint(1, 100) for _ in range(8)], random.randrange(10), random.randrange(2, 20, 3))
    print(round(random.uniform(1.0, 5.0), 6), round(random.gauss(0.0, 1.0), 6), round(random.gauss(10.0, 2.0), 6), random.getrandbits(20))
    xs = list(range(10))
    random.shuffle(xs)
    print(xs, random.choice(xs), random.sample(xs, 3), random.sample(range(100), 8))
    print(random.choices(["a", "b", "c"], k=5), random.choices([1, 2, 3], weights=[10, 1, 1], k=6))
    random.seed(2024)
    print(round(monte_carlo_pi(2000), 4))
    d = Dice(7)
    print([d.roll() for _ in range(10)], sum(d.rolls))
    r2 = random.Random(123)
    words = ["x", "y", "z", "w"]
    r2.shuffle(words)
    print(words, r2.choice(words), r2.random(), r2.sample(words, 2))
    random.seed(0)
    print(randint(0, 9), randint(0, 9))
    ys = [1, 2, 3, 4, 5]
    shuffle(ys)
    print(ys, random.expovariate(1.5))
    try:
        random.randrange(5, 5)
    except ValueError as e:
        print("error:", e)


if __name__ == "__main__":
    main()

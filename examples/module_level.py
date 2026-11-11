import math
from math import pi, sqrt

MOD = 1_000_000_007
GREETING = "hello"
PRIMES = [2, 3, 5, 7]
LIMITS: dict[str, int] = {"low": 1, "high": 9}
Grid = list[list[int]]
counter = 0
HISTORY = []


def bump() -> int:
    global counter
    counter += 1
    HISTORY.append(counter)
    return counter


def area(r: float) -> float:
    return pi * r ** 2


def make_grid(n: int) -> Grid:
    return [[i * j % MOD for j in range(n)] for i in range(n)]


def total() -> int:
    return sum(PRIMES) % MOD


print(GREETING, MOD, total())
for p in PRIMES:
    print(p, sqrt(p), math.floor(math.sqrt(p)))
print(bump(), bump(), counter, HISTORY)
print(area(2.0), make_grid(3), LIMITS["high"])
print(math.gcd(12, 18), math.ceil(2.1), math.log(8, 2), math.e, math.inf, -math.inf, math.isnan(math.nan))
squares = [x * x for x in range(5)]
print(squares, math.factorial(10), math.isqrt(99), math.lcm(4, 6), math.degrees(math.pi))
total_sq = 0
for s in squares:
    total_sq += s
print(total_sq)

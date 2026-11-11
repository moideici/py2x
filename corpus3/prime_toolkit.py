import math
from functools import lru_cache


def sieve(n: int) -> list[int]:
    if n < 2:
        return []
    flags = [True] * (n + 1)
    flags[0] = flags[1] = False
    for i in range(2, int(n ** 0.5) + 1):
        if flags[i]:
            for j in range(i * i, n + 1, i):
                flags[j] = False
    return [i for i, f in enumerate(flags) if f]


def factorize(n: int) -> dict[int, int]:
    result: dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            result[d] = result.get(d, 0) + 1
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        result[n] = result.get(n, 0) + 1
    return result


def divisors(n: int) -> list[int]:
    small: list[int] = []
    large: list[int] = []
    for d in range(1, math.isqrt(n) + 1):
        if n % d == 0:
            small.append(d)
            if d != n // d:
                large.append(n // d)
    return small + large[::-1]


@lru_cache(maxsize=None)
def collatz_len(n: int) -> int:
    if n == 1:
        return 1
    return 1 + collatz_len(n // 2 if n % 2 == 0 else 3 * n + 1)


def is_perfect(n: int) -> bool:
    return n > 1 and sum(divisors(n)) - n == n


def totient(n: int) -> int:
    result = n
    for p in factorize(n):
        result = result // p * (p - 1)
    return result


def modinv(a: int, m: int) -> int:
    g, x, y = extended_gcd(a, m)
    if g != 1:
        raise ValueError(f"{a} has no inverse mod {m}")
    return x % m


def extended_gcd(a: int, b: int) -> tuple[int, int, int]:
    if b == 0:
        return a, 1, 0
    g, x, y = extended_gcd(b, a % b)
    return g, y, x - (a // b) * y


def main() -> None:
    ps = sieve(60)
    print(ps, len(sieve(1000)), sieve(1))
    print(factorize(360), factorize(97), factorize(1001), factorize(2 ** 20))
    print(divisors(36), divisors(97), [n for n in range(2, 500) if is_perfect(n)])
    best = max(range(1, 3000), key=collatz_len)
    print(best, collatz_len(best), collatz_len(27))
    print([totient(n) for n in (1, 9, 10, 36, 97)], math.gcd(84, 36), math.lcm(4, 6))
    print(modinv(3, 11), modinv(10, 17), pow(3, 9, 11))
    try:
        modinv(6, 9)
    except ValueError as e:
        print("error:", e)


if __name__ == "__main__":
    main()

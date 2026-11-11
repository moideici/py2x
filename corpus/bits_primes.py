import math

MOD = 10**9 + 7


def popcount(x: int) -> int:
    count = 0
    while x:
        x &= x - 1
        count += 1
    return count


def gray(n: int) -> list[int]:
    return [i ^ (i >> 1) for i in range(1 << n)]


def sieve(limit: int) -> list[int]:
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(math.sqrt(limit)) + 1):
        if is_prime[i]:
            for j in range(i * i, limit + 1, i):
                is_prime[j] = False
    return [i for i, p in enumerate(is_prime) if p]


def power_mod(base: int, exp: int, mod: int = MOD) -> int:
    result = 1
    base %= mod
    while exp > 0:
        if exp & 1:
            result = result * base % mod
        base = base * base % mod
        exp >>= 1
    return result


def factorize(n: int) -> dict[int, int]:
    factors: dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors


def main() -> None:
    print(popcount(255), popcount(1 << 20), bin(10), hex(255), (37).bit_length())
    print(gray(3))
    ps = sieve(50)
    print(ps, len(ps))
    print(power_mod(2, 100), power_mod(3, 200, 1000))
    print(factorize(360), factorize(97), math.gcd(84, 36), math.floor(2.7), math.ceil(2.1))
    print(round(math.sqrt(2), 4), abs(-7), divmod(17, 5), pow(2, 10), max(3, 9, 4), min([4, 2, 8]))


if __name__ == "__main__":
    main()

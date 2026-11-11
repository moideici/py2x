def sieve(n: int) -> list[bool]:
    flags: list[bool] = []
    for i in range(n + 1):
        flags.append(True)
    flags[0] = False
    if n >= 1:
        flags[1] = False
    k: int = 2
    while k * k <= n:
        if flags[k]:
            j: int = k * k
            while j <= n:
                flags[j] = False
                j += k
        k += 1
    return flags


def count_true(flags: list[bool]) -> int:
    c: int = 0
    for f in flags:
        if f:
            c += 1
    return c


def main() -> None:
    f: list[bool] = sieve(100)
    print(count_true(f))
    primes: list[int] = []
    for p in range(len(f)):
        if f[p]:
            primes.append(p)
    print(primes)
    print(sum(primes), max(primes), min(primes))


if __name__ == "__main__":
    main()

def collatz_len(n: int) -> int:
    steps: int = 0
    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1
        steps += 1
    return steps


def sqrt_newton(x: float) -> float:
    g: float = x / 2.0
    for _ in range(30):
        g = (g + x / g) / 2.0
    return g


def main() -> None:
    best: int = 0
    best_n: int = 0
    for n in range(1, 30):
        if n % 5 == 0:
            continue
        s: int = collatz_len(n)
        if s > best:
            best = s
            best_n = n
        if s > 100:
            break
    print(best_n, best)
    total: int = 0
    for i in range(10, 0, -3):
        total += i
    print(total)
    print(sqrt_newton(2.0))


if __name__ == "__main__":
    main()

def gcd(a: int, b: int) -> int:
    while b != 0:
        a, b = b, a % b
    return a


def main() -> None:
    print(gcd(48, 18), gcd(17, 5), gcd(0, 9))
    print(-7 // 2, -7 % 3, 7 // -2, 7 % -3)
    print(7 / 2, 2 ** 10, 3 * 1.5, 10 / 4)
    x: float = 1.0
    x += 2
    print(x, x / 3)
    print(abs(-3), abs(-2.5), int(3.9), int(-3.9), float(2))
    print(min(3, 7), max(2.0, 9.5), max(10.0, 9.5), 5 > 3 and 2 < 1)
    print(1 < 2 < 3, 3 < 2 < 5, 7 & 3, 5 | 2, 5 ^ 1, 1 << 4, -16 >> 2)
    print(0.1 + 0.2, 1e16, 1.5e-7, 100.0, 12345678.9)


if __name__ == "__main__":
    main()

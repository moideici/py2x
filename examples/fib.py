def fib(n: int) -> int:
    a: int = 0
    b: int = 1
    for _ in range(n):
        a, b = b, a + b
    return a


def main() -> None:
    for i in range(10):
        print(i, fib(i))
    print(fib(50))


if __name__ == "__main__":
    main()

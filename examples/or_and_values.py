def f(a: str, n: int) -> str:
    return a.strip() or "dflt"


def g(n: int, m: int) -> int:
    return (n or 5) + (m and 3)


def main() -> None:
    print(f("  x ", 1), f("  ", 1), g(0, 1), g(2, 0), "" or "z", 0 or 7)


if __name__ == "__main__":
    main()

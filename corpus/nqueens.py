def solve(n: int) -> list[list[int]]:
    solutions: list[list[int]] = []
    cols: set[int] = set()
    diag1: set[int] = set()
    diag2: set[int] = set()
    placement: list[int] = []

    def place(row: int) -> None:
        if row == n:
            solutions.append(placement[:])
            return
        for c in range(n):
            if c in cols or (row - c) in diag1 or (row + c) in diag2:
                continue
            cols.add(c)
            diag1.add(row - c)
            diag2.add(row + c)
            placement.append(c)
            place(row + 1)
            placement.pop()
            cols.remove(c)
            diag1.remove(row - c)
            diag2.remove(row + c)

    place(0)
    return solutions


def main() -> None:
    for n in range(4, 8):
        sols = solve(n)
        print(f"n={n}: {len(sols)} solutions, first: {sols[0] if sols else None}")


if __name__ == "__main__":
    main()

Matrix = list[list[float]]


def identity(n: int) -> Matrix:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def multiply(a: Matrix, b: Matrix) -> Matrix:
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def transpose(m: Matrix) -> Matrix:
    return [list(row) for row in zip(*m)]


def determinant(m: Matrix) -> float:
    n = len(m)
    if n == 1:
        return m[0][0]
    if n == 2:
        return m[0][0] * m[1][1] - m[0][1] * m[1][0]
    total = 0.0
    for c in range(n):
        minor = [row[:c] + row[c + 1:] for row in m[1:]]
        total += ((-1) ** c) * m[0][c] * determinant(minor)
    return total


def spiral(m: list[list[int]]) -> list[int]:
    out: list[int] = []
    while m:
        out += m.pop(0)
        m = [list(r) for r in zip(*m)][::-1]
    return out


def main() -> None:
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[0.0, 1.0], [1.0, 0.0]]
    print(multiply(a, b), transpose(a), determinant(a))
    print(determinant([[2.0, 0.0, 1.0], [1.0, 3.0, 2.0], [1.0, 1.0, 1.0]]))
    print(multiply(a, identity(2)) == a)
    print(spiral([[1, 2, 3], [4, 5, 6], [7, 8, 9]]))


if __name__ == "__main__":
    main()

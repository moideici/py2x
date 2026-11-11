import math


class Vec:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __add__(self, other: "Vec") -> "Vec":
        return Vec(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec") -> "Vec":
        return Vec(self.x - other.x, self.y - other.y)

    def __mul__(self, k: float) -> "Vec":
        return Vec(self.x * k, self.y * k)

    def __neg__(self) -> "Vec":
        return Vec(-self.x, -self.y)

    def __eq__(self, other: "Vec") -> bool:
        return self.x == other.x and self.y == other.y

    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f})"

    def __repr__(self) -> str:
        return f"Vec({self.x}, {self.y})"

    def dot(self, other: "Vec") -> float:
        return self.x * other.x + self.y * other.y

    def length(self) -> float:
        return math.sqrt(self.dot(self))

    @property
    def angle(self) -> float:
        return math.degrees(math.atan2(self.y, self.x))

    @staticmethod
    def origin() -> "Vec":
        return Vec(0.0, 0.0)


class Matrix:
    def __init__(self, rows: list[list[int]]) -> None:
        self.rows = rows

    @classmethod
    def identity(cls, n: int) -> "Matrix":
        return cls([[1 if i == j else 0 for j in range(n)] for i in range(n)])

    def __mul__(self, other: "Matrix") -> "Matrix":
        n, m, p = len(self.rows), len(other.rows), len(other.rows[0])
        res = [[0] * p for _ in range(n)]
        for i in range(n):
            for j in range(p):
                for k in range(m):
                    res[i][j] += self.rows[i][k] * other.rows[k][j]
        return Matrix(res)

    def __getitem__(self, i: int) -> list[int]:
        return self.rows[i]

    def __len__(self) -> int:
        return len(self.rows)

    def __str__(self) -> str:
        return "\n".join(" ".join(f"{v:3d}" for v in row) for row in self.rows)

    def power(self, e: int) -> "Matrix":
        result = Matrix.identity(len(self.rows))
        base = self
        while e > 0:
            if e & 1:
                result = result * base
            base = base * base
            e >>= 1
        return result


def main() -> None:
    a = Vec(3.0, 4.0)
    b = Vec(1.0, -2.0)
    print(a + b, a - b, a * 2.0, -a, a.length(), a == Vec(3.0, 4.0), a == b)
    print(repr(a), round(a.angle, 3), Vec.origin())
    print(a.dot(b))
    fibm = Matrix([[1, 1], [1, 0]])
    p = fibm.power(10)
    print(p)
    print(p[0][1], len(p), len(Matrix.identity(3)))


if __name__ == "__main__":
    main()

class Polynomial:
    def __init__(self, coeffs: list[int]) -> None:
        cs = list(coeffs)
        while len(cs) > 1 and cs[-1] == 0:
            cs.pop()
        self.coeffs = cs

    @property
    def degree(self) -> int:
        return len(self.coeffs) - 1

    def __add__(self, other: "Polynomial") -> "Polynomial":
        n = max(len(self.coeffs), len(other.coeffs))
        a = self.coeffs + [0] * (n - len(self.coeffs))
        b = other.coeffs + [0] * (n - len(other.coeffs))
        return Polynomial([x + y for x, y in zip(a, b)])

    def __sub__(self, other: "Polynomial") -> "Polynomial":
        return self + (-other)

    def __neg__(self) -> "Polynomial":
        return Polynomial([-c for c in self.coeffs])

    def __mul__(self, other: "Polynomial") -> "Polynomial":
        res = [0] * (len(self.coeffs) + len(other.coeffs) - 1)
        for i, a in enumerate(self.coeffs):
            for j, b in enumerate(other.coeffs):
                res[i + j] += a * b
        return Polynomial(res)

    def __eq__(self, other: "Polynomial") -> bool:
        return self.coeffs == other.coeffs

    def __call__(self, x: int) -> int:
        return self.evaluate(x)

    def evaluate(self, x: int) -> int:
        result = 0
        for c in reversed(self.coeffs):
            result = result * x + c
        return result

    def derivative(self) -> "Polynomial":
        if len(self.coeffs) == 1:
            return Polynomial([0])
        return Polynomial([i * c for i, c in enumerate(self.coeffs)][1:])

    def __str__(self) -> str:
        terms: list[str] = []
        for i in range(len(self.coeffs) - 1, -1, -1):
            c = self.coeffs[i]
            if c == 0 and len(self.coeffs) > 1:
                continue
            sign = "-" if c < 0 else "+"
            mag = abs(c)
            if i == 0:
                body = str(mag)
            else:
                coef = "" if mag == 1 else str(mag)
                body = coef + "x" + ("" if i == 1 else "^" + str(i))
            terms.append(sign + " " + body)
        text = " ".join(terms)
        return text[2:] if text.startswith("+ ") else "-" + text[2:] if text.startswith("- ") else text


def main() -> None:
    p = Polynomial([1, -3, 0, 2])
    q = Polynomial([-1, 1])
    print(p, "|", q, "|", p.degree, q.degree)
    print(p + q, "|", p - q, "|", p * q, "|", -q)
    print(p.derivative(), "|", p.derivative().derivative().derivative().derivative(), "|", Polynomial([0, 0, 0]))
    print([p.evaluate(x) for x in range(-2, 3)], p.evaluate(10), q.evaluate(1))
    print(p == Polynomial([1, -3, 0, 2, 0]), p == q, (p * q).degree)


if __name__ == "__main__":
    main()

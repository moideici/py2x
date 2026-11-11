from typing import Optional


class Expr:
    def eval(self, env: dict[str, float]) -> float:
        raise NotImplementedError("eval")

    def show(self) -> str:
        return "?"

    def depth(self) -> int:
        return 1


class Num(Expr):
    def __init__(self, value: float) -> None:
        self.value = value

    def eval(self, env: dict[str, float]) -> float:
        return self.value

    def show(self) -> str:
        return str(self.value)


class Var(Expr):
    def __init__(self, name: str) -> None:
        self.name = name

    def eval(self, env: dict[str, float]) -> float:
        if self.name not in env:
            raise KeyError(self.name)
        return env[self.name]

    def show(self) -> str:
        return self.name


class BinOp(Expr):
    def __init__(self, op: str, left: Expr, right: Expr) -> None:
        self.op = op
        self.left = left
        self.right = right

    def eval(self, env: dict[str, float]) -> float:
        a = self.left.eval(env)
        b = self.right.eval(env)
        if self.op == "+":
            return a + b
        if self.op == "-":
            return a - b
        if self.op == "*":
            return a * b
        if self.op == "/":
            if b == 0.0:
                raise ZeroDivisionError("division by zero in expression")
            return a / b
        raise ValueError("unknown operator " + self.op)

    def show(self) -> str:
        return "(" + self.left.show() + " " + self.op + " " + self.right.show() + ")"

    def depth(self) -> int:
        return 1 + max(self.left.depth(), self.right.depth())


def simplify(e: Expr) -> Expr:
    if isinstance(e, BinOp):
        l = simplify(e.left)
        r = simplify(e.right)
        if isinstance(l, Num) and isinstance(r, Num):
            return Num(BinOp(e.op, l, r).eval({}))
        if e.op == "*" and isinstance(r, Num) and r.value == 1.0:
            return l
        if e.op == "+" and isinstance(r, Num) and r.value == 0.0:
            return l
        return BinOp(e.op, l, r)
    return e


def find_var(e: Expr, name: str) -> Optional[Var]:
    if isinstance(e, Var):
        return e if e.name == name else None
    if isinstance(e, BinOp):
        found = find_var(e.left, name)
        if found is not None:
            return found
        return find_var(e.right, name)
    return None


def main() -> None:
    e = BinOp("+", BinOp("*", Var("x"), Num(1.0)), BinOp("*", Num(2.0), Num(3.5)))
    print(e.show(), e.depth())
    s = simplify(e)
    print(s.show(), s.depth())
    print(e.eval({"x": 4.0}), s.eval({"x": 4.0}))
    print(find_var(e, "x") is not None, find_var(e, "y") is None)
    for bad in (BinOp("/", Num(1.0), Num(0.0)), Var("zz"), BinOp("^", Num(1.0), Num(2.0))):
        try:
            print(bad.eval({}))
        except ZeroDivisionError as ex:
            print("zde", ex)
        except KeyError as ex:
            print("key", ex)
        except ValueError as ex:
            print("value", ex)


if __name__ == "__main__":
    main()

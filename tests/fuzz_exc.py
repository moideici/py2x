"""Fuzzer différentiel : exceptions, try/except/else/finally, héritage et méthodes virtuelles, comparés à Python.

  python tests/fuzz_exc.py --target cpp --seeds 20
  python tests/fuzz_exc.py --target kotlin --seeds 3
"""
import argparse
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from py2x import Unsupported, transpile  # noqa: E402
from py2x.verify import build_and_run, python_output  # noqa: E402

HEADER = '''class E0(Exception):
    pass


class E1(E0):
    def __init__(self, code: int) -> None:
        super().__init__(f"code {code}")
        self.code = code


class E2(Exception):
    pass


class Base:
    def __init__(self, k: int) -> None:
        self.k = k

    def val(self, x: int) -> int:
        return self.k + x

    def check(self, x: int) -> int:
        if x < 0:
            raise ValueError("neg " + str(x))
        return x * 2

    def __str__(self) -> str:
        return "Base" + str(self.k)


class Mid(Base):
    def val(self, x: int) -> int:
        return super().val(x) * 2

    def check(self, x: int) -> int:
        if x > 50:
            raise E0("big")
        return super().check(x)


class Leaf(Mid):
    def __init__(self, k: int, m: int) -> None:
        super().__init__(k)
        self.m = m

    def val(self, x: int) -> int:
        return super().val(x) + self.m

    def __str__(self) -> str:
        return "Leaf" + str(self.k) + "/" + str(self.m)


'''

EXC_TYPES = ["ZeroDivisionError", "IndexError", "KeyError", "ValueError", "E0", "E1", "E2", "Exception", "ArithmeticError", "LookupError"]


class Gen:
    def __init__(self, seed):
        self.r = random.Random(seed)
        self.nfun = 0

    def expr(self, depth=0):
        r = self.r
        k = r.randrange(12 if depth < 2 else 5)
        if k == 0:
            return str(r.randint(-5, 9))
        if k == 1:
            return r.choice(["a", "b", "c"])
        if k == 2:
            return f"len(xs)"
        if k == 3:
            return f"{r.choice(['a', 'b'])} % 3"
        if k == 4:
            return f"d[{r.choice(['a', 'b'])} % 4]"
        if k == 5:
            return f"xs[{self.expr(depth + 1)}]"
        if k == 6:
            return f"({self.expr(depth + 1)}) // ({self.expr(depth + 1)})"
        if k == 7:
            return f"({self.expr(depth + 1)}) + ({self.expr(depth + 1)})"
        if k == 8:
            return f"({self.expr(depth + 1)}) - ({self.expr(depth + 1)})"
        if k == 9:
            return f"int(s[{r.randint(0, 3)}])"
        if k == 10:
            return f"obj.val({self.expr(depth + 1)})"
        return f"obj.check({self.expr(depth + 1)})"

    def cond(self):
        return f"({self.expr(2)}) {self.r.choice(['<', '>', '==', '!=', '<=', '>='])} ({self.expr(2)})"

    def exc_expr(self):
        t = self.r.choice(["ZeroDivisionError", "ValueError", "E0", "E1", "E2", "Exception", "RuntimeError", "KeyError"])
        if t == "E1":
            return f"E1({self.expr(2)})"
        return f"{t}('m' + str({self.expr(2)}))"

    def stmt(self, depth, in_loop, ind, can_return):
        r = self.r
        pad = "    " * ind
        k = r.randrange(14 if depth < 3 else 6)
        out = []
        if k <= 1:
            out.append(f"{pad}{r.choice(['a', 'b', 'c'])} = {self.expr()}")
        elif k == 2:
            out.append(f"{pad}print('v', {self.expr()}, a, b, c)")
        elif k == 3:
            out.append(f"{pad}if {self.cond()}:")
            out += self.block(depth + 1, in_loop, ind + 1, can_return)
            if r.randrange(2):
                out.append(f"{pad}else:")
                out += self.block(depth + 1, in_loop, ind + 1, can_return)
        elif k == 4:
            out.append(f"{pad}if {self.cond()}:")
            out.append(f"{pad}    raise {self.exc_expr()}")
        elif k == 5 and can_return:
            out.append(f"{pad}if {self.cond()}:")
            out.append(f"{pad}    return {self.expr()}")
        elif k == 6 and in_loop:
            out.append(f"{pad}if {self.cond()}:")
            out.append(f"{pad}    {r.choice(['break', 'continue'])}")
        elif k in (7, 8, 9):
            out.append(f"{pad}try:")
            out += self.block(depth + 1, in_loop, ind + 1, can_return)
            nh = r.randint(1, 3)
            for _ in range(nh):
                types = r.sample(EXC_TYPES, r.randint(1, 2))
                head = types[0] if len(types) == 1 else "(" + ", ".join(types) + ")"
                if r.randrange(6) == 0:
                    out.append(f"{pad}except:")
                    out.append(f"{pad}    print('bare')")
                    break
                use_var = r.randrange(3) > 0
                out.append(f"{pad}except {head}" + (" as e:" if use_var else ":"))
                if use_var:
                    out.append(f"{pad}    print('caught', e, a)")
                else:
                    out.append(f"{pad}    print('caught-novar', b)")
                if r.randrange(5) == 0:
                    out.append(f"{pad}    raise")
                elif r.randrange(6) == 0:
                    out.append(f"{pad}    raise E2('re' + str(a))")
                else:
                    out.append(f"{pad}    c = c + 1")
            if r.randrange(3) == 0:
                out.append(f"{pad}else:")
                out.append(f"{pad}    print('else', a)")
            if r.randrange(2):
                out.append(f"{pad}finally:")
                out.append(f"{pad}    print('fin', a, b)")
                out.append(f"{pad}    c = c + 10")
            elif not any(ln.strip().startswith("except") for ln in out[-12:]):
                out.append(f"{pad}finally:")
                out.append(f"{pad}    print('fin2')")
        elif k == 10:
            n = r.randint(0, 4)
            out.append(f"{pad}for i in range({n}):")
            out.append(f"{pad}    a = a + i")
            out += self.block(depth + 1, True, ind + 1, can_return)
        elif k == 11 and self.nfun > 0:
            out.append(f"{pad}a = f{r.randrange(self.nfun)}({self.expr(2)}, {self.expr(2)})")
        elif k == 12:
            out.append(f"{pad}print('obj', obj, obj.val({self.expr(2)}))")
        else:
            out.append(f"{pad}c = c + 1")
        return out

    def block(self, depth, in_loop, ind, can_return):
        n = self.r.randint(1, 3)
        out = []
        for _ in range(n):
            out += self.stmt(depth, in_loop, ind, can_return)
        return out

    def function(self):
        i = self.nfun
        body = []
        for _ in range(self.r.randint(2, 5)):
            body += self.stmt(0, False, 1, True)
        self.nfun += 1
        kinds = ["Base(3)", "Mid(2)", "Leaf(1, 4)"]
        lines = [f"def f{i}(a: int, b: int) -> int:", "    c = 0", f"    obj: Base = {self.r.choice(kinds)}",
                 "    xs = [1, 2, 3, 4]", "    d = {0: 5, 1: 6, 2: 7}", "    s = '12x4'"]
        lines += body
        lines.append("    return a + b + c")
        return "\n".join(lines) + "\n\n\n"


def program(seed):
    g = Gen(seed)
    funcs = "".join(g.function() for _ in range(g.r.randint(3, 5)))
    calls = []
    for i in range(g.nfun):
        for x, y in [(1, 2), (0, 0), (-3, 7), (5, 1)]:
            calls.append(f"    try:\n        print('f{i}', {x}, {y}, '->', f{i}({x}, {y}))\n"
                         f"    except Exception as e:\n        print('f{i}', {x}, {y}, 'raised', e)\n")
    return HEADER + funcs + "def main() -> None:\n" + "".join(calls) + "\n\nif __name__ == \"__main__\":\n    main()\n"


def run_seed(seed, target):
    src = program(seed)
    path = Path(tempfile.mkdtemp(prefix="fuzze_")) / "prog.py"
    path.write_text(src, encoding="utf-8")
    try:
        expected = python_output(path)
    except RuntimeError as ex:
        return [], 0, src, f"seed {seed}: programme Python invalide (ignoré) : {str(ex)[:120]}"
    try:
        code = transpile(src, target)
    except Unsupported as ex:
        return [f"seed {seed}: Unsupported : {ex}"], 0, src, ""
    got, err = build_and_run(code, target)
    if err:
        return [f"seed {seed}: {err[:1500]}"], 0, src, ""
    got, exp = got.replace("\r\n", "\n").splitlines(), expected.splitlines()
    bad = [f"seed {seed}: {len(got)} lignes obtenues, {len(exp)} attendues"] if len(got) != len(exp) else []
    for i, (a, b) in enumerate(zip(exp, got)):
        if a != b:
            bad.append(f"seed {seed} ligne {i + 1}:\n      Python={a}\n      {target}={b}")
    return bad, len(exp), src, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["cpp", "kotlin"], required=True)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--first", type=int, default=1)
    a = ap.parse_args()
    total, failures = 0, []
    for seed in range(a.first, a.first + a.seeds):
        bad, n, src, note = run_seed(seed, a.target)
        total += n
        failures += bad
        print(f"seed {seed} : {n} lignes comparées, {len(bad)} écart(s) {note}", flush=True)
        if bad and not (ROOT / "tests" / "fuzz_failure.py").exists():
            (ROOT / "tests" / "fuzz_failure.py").write_text(src, encoding="utf-8")
    for f in failures[:12]:
        print("  ÉCART", f)
    print(f"\n{total} lignes comparées, {len(failures)} écart(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

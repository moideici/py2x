"""Fuzzer différentiel : expressions arithmétiques aléatoires, Python vs C++ / Kotlin, comparées ligne à ligne.

  python tests/fuzz_expr.py --target cpp --seeds 3 --n 150
  python tests/fuzz_expr.py --target kotlin --seeds 2
Les compilations tournent en priorité basse. Code de sortie 1 si un écart est trouvé.
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

CALLS = [(7, -3, 12, 1.5, -0.25), (-5, 4, 0, 2.0, 3.5), (13, 13, -1, -7.75, 0.5), (0, -9, 8, 1e-3, 123.456)]
IVARS, FVARS = ["a", "b", "c"], ["x", "y"]


class Gen:
    def __init__(self, rng):
        self.r = rng

    def leaf_int(self):
        return self.r.choice(IVARS) if self.r.random() < 0.6 else str(self.r.randint(-20, 20))

    def nonzero(self):
        return self.r.choice([f"(abs({self.leaf_int()}) + 1)", str(self.r.choice([-7, -3, -2, -1, 1, 2, 3, 5, 9]))])

    def int(self, d):
        if d == 0 or self.r.random() < 0.15:
            return self.leaf_int()
        k = self.r.randrange(12)
        l, r = self.int(d - 1), self.int(d - 1)
        if k == 0:
            return f"({l} + {r})"
        if k == 1:
            return f"({l} - {r})"
        if k == 2:
            return f"({l} * {r})"
        if k == 3:
            return f"({l} // {self.nonzero()})"
        if k == 4:
            return f"({l} % {self.nonzero()})"
        if k == 5:
            return f"({self.leaf_int()} ** {self.r.randint(0, 3)})"
        if k == 6:
            return f"({l} {self.r.choice(['&', '|', '^'])} {r})"
        if k == 7:
            return f"({l} {self.r.choice(['<<', '>>'])} {self.r.randint(0, 5)})"
        if k == 8:
            return f"abs({l})"
        if k == 9:
            return f"{self.r.choice(['min', 'max'])}({l}, {r})"
        if k == 10:
            return f"(-{l})"
        return f"({l} if {self.bool(d - 1)} else {r})"

    def flt_leaf(self):
        return self.r.choice(FVARS) if self.r.random() < 0.6 else self.r.choice(["0.5", "1.25", "-3.75", "2.0", "0.1", "100.0"])

    def flt(self, d):
        if d == 0 or self.r.random() < 0.15:
            return self.flt_leaf()
        k = self.r.randrange(9)
        l, r = self.flt(d - 1), self.flt(d - 1)
        if k == 0:
            return f"({l} + {r})"
        if k == 1:
            return f"({l} - {r})"
        if k == 2:
            return f"({l} * {r})"
        if k == 3:
            return f"({l} / ({r} * {r} + 1.0))"
        if k == 4:
            return f"({self.int(d - 1)} / {self.nonzero()})"
        if k == 5:
            return f"float({self.int(d - 1)})"
        if k == 6:
            return f"abs({l})"
        if k == 7:
            return f"{self.r.choice(['min', 'max'])}({l}, float({self.int(d - 1)}))"
        return f"({l} + {self.int(d - 1)})"

    def bool(self, d):
        k = self.r.randrange(5)
        if k == 0:
            return f"({self.int(d)} {self.r.choice(['<', '<=', '>', '>=', '==', '!='])} {self.int(d)})"
        if k == 1:
            return f"({self.flt(d)} {self.r.choice(['<', '>', '<=', '>='])} {self.flt(d)})"
        if k == 2 and d > 0:
            return f"({self.bool(d - 1)} {self.r.choice(['and', 'or'])} {self.bool(d - 1)})"
        if k == 3 and d > 0:
            return f"(not {self.bool(d - 1)})"
        return f"({self.int(d)} < {self.int(d)} < {self.int(d)})" if False else f"({self.int(d)} == {self.int(d)})"

    def stmt(self):
        k = self.r.randrange(10)
        if k < 5:
            return self.int(3)
        if k < 8:
            return self.flt(3)
        if k < 9:
            return self.bool(2)
        return f"int({self.flt(2)})" if False else f"({self.int(2)} / {self.nonzero()})"


def program(seed, n):
    g, exprs = Gen(random.Random(seed)), []
    while len(exprs) < n:
        e = g.stmt()
        if len(e) < 400:
            exprs.append(e)
    body = "\n".join(f"    print({e})" for e in exprs)
    calls = "\n".join(f"    f({a}, {b}, {c}, {x!r}, {y!r})" for a, b, c, x, y in CALLS)
    src = (f"def f(a: int, b: int, c: int, x: float, y: float) -> None:\n{body}\n\n\n"
           f"def main() -> None:\n{calls}\n\n\nif __name__ == \"__main__\":\n    main()\n")
    return src, exprs


def run_seed(seed, n, target):
    src, exprs = program(seed, n)
    path = Path(tempfile.mkdtemp(prefix="fuzz_")) / "prog.py"
    path.write_text(src, encoding="utf-8")
    expected = python_output(path).splitlines()
    try:
        code = transpile(src, target)
    except Unsupported as e:
        return [f"seed {seed}: Unsupported : {e}"], 0
    got, err = build_and_run(code, target)
    if err:
        return [f"seed {seed}: {err[:700]}"], 0
    got = got.replace("\r\n", "\n").splitlines()
    bad = []
    if len(got) != len(expected):
        bad.append(f"seed {seed}: {len(got)} lignes obtenues, {len(expected)} attendues")
    for i, (e, g_) in enumerate(zip(expected, got)):
        if e != g_:
            bad.append(f"seed {seed} appel {i // len(exprs)} : {exprs[i % len(exprs)]}\n      Python={e}   {target}={g_}")
    return bad, len(expected)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["cpp", "kotlin"], required=True)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--n", type=int, default=150)
    a = ap.parse_args()
    total, failures = 0, []
    for seed in range(a.first, a.first + a.seeds):
        bad, n = run_seed(seed, a.n, a.target)
        total += n
        failures += bad
        print(f"seed {seed} : {n} valeurs comparées, {len(bad)} écart(s)", flush=True)
    for f in failures[:25]:
        print("  ÉCART", f)
    print(f"\n{total} valeurs comparées, {len(failures)} écart(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

"""Fuzzer différentiel des classes : aliasing d'objets, mutation via liste/dict/boucle, dataclasses imbriquées, égalité par valeur.

  python tests/fuzz_classes.py --target cpp --seeds 15
  python tests/fuzz_classes.py --target kotlin --seeds 3
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

HEADER = '''from dataclasses import dataclass, field


@dataclass
class Point:
    x: int
    y: int = 0

    def move(self, dx: int, dy: int = 0) -> None:
        self.x += dx
        self.y += dy

    def norm1(self) -> int:
        return abs(self.x) + abs(self.y)


@dataclass
class Seg:
    a: Point
    b: Point
    tag: str = "s"

    def span(self) -> int:
        return abs(self.a.x - self.b.x) + abs(self.a.y - self.b.y)


@dataclass(frozen=True)
class Tag:
    name: str
    w: int = 1


@dataclass
class Bag:
    items: list[int] = field(default_factory=list)
    label: str = "bag"


class Box:
    def __init__(self, n: int) -> None:
        self.n = n
        self.items: list[int] = []

    def add(self, v: int) -> "Box":
        self.items.append(v)
        self.n += 1
        return self

    def total(self) -> int:
        t: int = 0
        for v in self.items:
            t += v
        return t

    def __str__(self) -> str:
        return f"Box({self.n}, {self.items})"


def grow(p: Point, k: int) -> None:
    p.x += k
    p.y -= k


def main() -> None:
'''

PTS = ["p0", "p1", "p2"]
SEGS = ["s0", "s1"]
BOXES = ["b0", "b1"]


def body(seed, n):
    r = random.Random(seed)
    L = ["    p0 = Point(1, 2)", "    p1 = Point(3)", "    p2 = Point(y=5, x=-4)",
         "    s0 = Seg(p0, p1)", "    s1 = Seg(p1, p2, \"t\")", "    b0 = Box(0)", "    b1 = Box(10)",
         "    pts: list[Point] = []", "    d: dict[str, Point] = {}", "    segs: list[Seg] = []", "    bag = Bag()"]
    for k in range(n):
        p, q = r.choice(PTS), r.choice(PTS)
        s, b = r.choice(SEGS), r.choice(BOXES)
        v, w = r.randint(-5, 9), r.randint(-3, 3)
        op = r.randrange(26)
        if op == 0:
            L.append(f"    {p}.move({v}, {w})")
        elif op == 1:
            L.append(f"    {p}.move(dy={w}, dx={v})")
        elif op == 2:
            L.append(f"    {p} = {q}")
        elif op == 3:
            L.append(f"    pts.append({p})")
        elif op == 4:
            L.append(f"    d[\"k{r.randint(0, 3)}\"] = {p}")
        elif op == 5:
            L.append(f"    print({p}, {q}, {p} == {q}, {p} in pts, {p}.norm1())")
        elif op == 6:
            L += ["    if len(pts) > 0:", f"        pts[0].x += {v}", f"        pts[len(pts) - 1].y -= {w}"]
        elif op == 7:
            L.append(f"    {s} = Seg({p}, {q}, \"u{k}\")")
        elif op == 8:
            L.append(f"    {s}.a.x += {v}")
        elif op == 9:
            L.append(f"    print({s}, {s}.span())")
        elif op == 10:
            L.append(f"    print(s0 == s1, {s} == Seg({p}, {q}, {s}.tag))")
        elif op == 11:
            L.append(f"    {b}.add({v}).add({w})")
        elif op == 12:
            L.append(f"    print({b}, {b}.total())")
        elif op == 13:
            L.append("    print(pts, len(pts))")
        elif op == 14:
            L.append("    print(d, len(d))")
        elif op == 15:
            L += ["    for q_ in pts:", f"        q_.y += {v}"]
        elif op == 16:
            L.append(f"    grow({p}, {v})")
        elif op == 17:
            L.append(f"    print(Tag(\"t\", {v}), Tag(\"t\", {v}) == Tag(\"t\", {w}), Tag(\"z\"))")
        elif op == 18:
            L.append(f"    tp: tuple[Point, int] = ({p}, {v})" if k == 0 or True else "")
            # redéclarer plusieurs fois la même variable est une affectation : le type reste identique
            L.append("    print(tp)")
        elif op == 19:
            L.append(f"    segs.append({s})")
        elif op == 20:
            L += ["    for sg in segs:", f"        sg.b.x += {w}", "        print(sg.tag, sg.span())"]
        elif op == 21:
            L.append(f"    bag.items.append({v})")
        elif op == 22:
            L.append(f"    print(bag, bag.label, len(bag.items))")
        elif op == 23:
            L += ["    for kk, pp in d.items():", f"        pp.x += {w}", "        print(kk, pp)"]
        elif op == 24:
            L.append(f"    print({p} in pts, {s} in segs, {q} == {p})")
        else:
            L.append(f"    bag = Bag([{v}, {w}], \"b{k}\")")
    L += ["    print(p0, p1, p2)", "    print(s0, s1)", "    print(pts)", "    print(d)", "    print(b0, b1)", "    print(bag)"]
    return "\n".join(L) + "\n"


def program(seed, n):
    return HEADER + body(seed, n) + "\n\nif __name__ == \"__main__\":\n    main()\n"


def run_seed(seed, n, target):
    src = program(seed, n)
    path = Path(tempfile.mkdtemp(prefix="fuzzc_")) / "prog.py"
    path.write_text(src, encoding="utf-8")
    expected = python_output(path)
    try:
        code = transpile(src, target)
    except Unsupported as ex:
        return [f"seed {seed}: Unsupported : {ex}"], 0, src
    got, err = build_and_run(code, target)
    if err:
        return [f"seed {seed}: {err[:1200]}"], 0, src
    got, exp = got.replace("\r\n", "\n").splitlines(), expected.splitlines()
    bad = [f"seed {seed}: {len(got)} lignes obtenues, {len(exp)} attendues"] if len(got) != len(exp) else []
    for i, (a, b) in enumerate(zip(exp, got)):
        if a != b:
            bad.append(f"seed {seed} ligne {i + 1}:\n      Python={a}\n      {target}={b}")
    return bad, len(exp), src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["cpp", "kotlin"], required=True)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--n", type=int, default=50)
    a = ap.parse_args()
    total, failures = 0, []
    for seed in range(a.first, a.first + a.seeds):
        bad, n, src = run_seed(seed, a.n, a.target)
        total += n
        failures += bad
        print(f"seed {seed} : {n} lignes comparées, {len(bad)} écart(s)", flush=True)
        if bad and not (ROOT / "tests" / "fuzz_failure.py").exists():
            (ROOT / "tests" / "fuzz_failure.py").write_text(src, encoding="utf-8")
    for f in failures[:10]:
        print("  ÉCART", f)
    print(f"\n{total} lignes comparées, {len(failures)} écart(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

"""Fuzzer différentiel de l'ALIASING : list/dict sont des références partagées en Python, doivent l'être exactement dans les cibles.

  python tests/fuzz_alias.py --target cpp --seeds 20
  python tests/fuzz_alias.py --target kotlin --seeds 3
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

HEADER = '''from dataclasses import dataclass


class Holder:
    def __init__(self, items: list[int]) -> None:
        self.items = items

    def get(self) -> list[int]:
        return self.items

    def add(self, v: int) -> None:
        self.items.append(v)


@dataclass
class Box:
    data: list[int]
    meta: dict[str, int]


def add(xs: list[int], v: int) -> list[int]:
    xs.append(v)
    return xs


def fresh(xs: list[int]) -> list[int]:
    ys = list(xs)
    ys.append(-1)
    return ys


def grow(d: dict[str, int], k: str, v: int) -> None:
    d[k] = v


def main() -> None:
'''

LISTS = ["A", "B", "C"]
DICTS = ["D", "E"]


def body(seed, n):
    r = random.Random(seed)
    L = ["    A = [1, 2]", "    B = [3]", "    C = [9, 8, 7]", "    D = {\"x\": 1}", "    E = {\"y\": 2}",
         "    H = Holder(A)", "    bx = Box(B, D)", "    grid = [A, B]", "    t = (A, 5)", "    rows = [[0] * 2] * 3",
         "    byname = {\"a\": A, \"b\": C}"]
    for k in range(n):
        x, y = r.choice(LISTS), r.choice(LISTS)
        dx, dy = r.choice(DICTS), r.choice(DICTS)
        v = r.randint(-5, 9)
        key = r.choice(["x", "y", "z", "w"])
        op = r.randrange(28)
        if op == 0:
            L.append(f"    {x} = {y}")
        elif op == 1:
            L.append(f"    {x} = list({y})")
        elif op == 2:
            L.append(f"    {x}.append({v})")
        elif op == 3:
            L.append(f"    {x} = {y} + [{v}]")
        elif op == 4:
            L.append(f"    {dx} = {dy}")
        elif op == 5:
            L.append(f"    {dx}[\"{key}\"] = {v}")
        elif op == 6:
            L.append(f"    H.add({v})")
        elif op == 7:
            L.append(f"    H.items = {x}")
        elif op == 8:
            L.append(f"    {x} = H.get()")
        elif op == 9:
            L.append(f"    {x} = add({y}, {v})")
        elif op == 10:
            L.append(f"    {x} = fresh({y})")
        elif op == 11:
            L.append(f"    grow({dx}, \"{key}\", {v})")
        elif op == 12:
            L.append(f"    bx.data.append({v})")
        elif op == 13:
            L.append(f"    bx = Box({x}, {dx})")
        elif op == 14:
            L.append(f"    bx.meta[\"{key}\"] = {v}")
        elif op == 15:
            L.append(f"    grid[{r.randint(0, 1)}].append({v})")
        elif op == 16:
            L.append(f"    grid = [{x}, {y}, {x}]")
        elif op == 17:
            L.append(f"    t = ({x}, {v})")
        elif op == 18:
            L.append(f"    t[0].append({v})")
        elif op == 19:
            L.append(f"    rows[{r.randint(0, 2)}][{r.randint(0, 1)}] = {v}")
        elif op == 20:
            L.append("    rows = [[0] * 2 for _ in range(3)]")
        elif op == 21:
            L.append(f"    byname[\"{r.choice('ab')}\"].append({v})")
        elif op == 22:
            L.append(f"    byname[\"c\"] = {x}")
        elif op == 23:
            L += [f"    for lst in grid:", f"        lst.append({v})"]
        elif op == 24:
            L.append(f"    print({x} == {y}, {dx} == {dy}, bx == Box({x}, {dx}))")
        elif op == 25:
            L.append(f"    q = {x}")
            L.append(f"    q.append({v})")
        elif op == 26:
            L.append("    print(grid, t, rows)")
        else:
            L.append(f"    print(A, B, C, D, E, H.items, bx, byname)")
    L += ["    print(A, B, C, D, E)", "    print(H.items, bx, grid, t, rows, byname)"]
    return "\n".join(L) + "\n"


def program(seed, n):
    return HEADER + body(seed, n) + "\n\nif __name__ == \"__main__\":\n    main()\n"


def run_seed(seed, n, target):
    src = program(seed, n)
    path = Path(tempfile.mkdtemp(prefix="fuzza_")) / "prog.py"
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
    ap.add_argument("--n", type=int, default=60)
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

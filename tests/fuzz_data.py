"""Fuzzer différentiel des structures de données : dict (ordre d'insertion, items/keys/values), tuples, tri de tuples.

  python tests/fuzz_data.py --target cpp --seeds 8
  python tests/fuzz_data.py --target kotlin --seeds 3
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

KEYS = [f"k{i}" for i in range(6)] + ["zz", "a b", "é"[:0] + "x"]  # ASCII uniquement : str = octets en C++
FLOATS = ["1.5", "0.25", "-2.0", "100.0", "0.1"]


def program(seed, n):
    r = random.Random(seed)
    L = ["    d: dict[str, int] = {}", "    e: dict[tuple[int, int], float] = {}", "    ps: list[tuple[int, str]] = []",
         "    t: tuple[int, str, float] = (1, \"a\", 2.5)"]
    for _ in range(n):
        k, i, j, v = r.choice(KEYS), r.randint(0, 3), r.randint(0, 3), r.randint(-9, 9)
        op = r.randrange(16)
        if op == 0:
            L.append(f"    d[\"{k}\"] = {v}")
        elif op == 1:
            L += [f"    if \"{k}\" in d:", f"        d[\"{k}\"] += {v}"]
        elif op == 2:
            L.append(f"    e[({i}, {j})] = {r.choice(FLOATS)}")
        elif op == 3:
            L.append(f"    ps.append(({v}, \"{k}\"))")
        elif op == 4:
            L.append(f"    print(d.get(\"{k}\", -1), len(d), len(e), len(ps))")
        elif op == 5:
            L += ["    for kk, vv in d.items():", "        print(kk, vv)"]
        elif op == 6:
            L.append("    print(list(d.keys()), list(d.values()), sum(d.values()))")
        elif op == 7:
            L.append("    print(d)")
        elif op == 8:
            L.append("    print(e)")
        elif op == 9:
            L.append("    print(sorted(ps))")
        elif op == 10:
            L += ["    ps.sort()", "    print(ps)"]
        elif op == 11:
            L += ["    for pa, pb in ps:", "        print(pa, pb, pa < 0)"]
        elif op == 12:
            L.append(f"    print(({i}, \"{k}\") < ({j}, \"{r.choice(KEYS)}\"), ({i}, {j}) == ({j}, {i}), ({i}, {j}) in e)")
        elif op == 13:
            L += ["    for ek, ev in e.items():", "        print(ek, ev, ek[0] + ek[1], ev * 2)"]
        elif op == 14:
            L.append("    print(t, t[0], t[1], t[2], t[-1])")
        else:
            L += [f"    x{_}, y{_} = {i}, \"{k}\"", f"    t = (x{_} + {j}, y{_}, t[2] / 4)"]
    L += ["    print(d)", "    print(e)", "    print(sorted(ps))", "    print(t)"]
    return "def main() -> None:\n" + "\n".join(L) + "\n\n\nif __name__ == \"__main__\":\n    main()\n"


def run_seed(seed, n, target):
    src = program(seed, n)
    path = Path(tempfile.mkdtemp(prefix="fuzzd_")) / "prog.py"
    path.write_text(src, encoding="utf-8")
    expected = python_output(path)
    try:
        code = transpile(src, target)
    except Unsupported as ex:
        return [f"seed {seed}: Unsupported : {ex}"], 0, src
    got, err = build_and_run(code, target)
    if err:
        return [f"seed {seed}: {err[:900]}"], 0, src
    got, exp = got.replace("\r\n", "\n").splitlines(), expected.splitlines()
    bad = [f"seed {seed}: {len(got)} lignes obtenues, {len(exp)} attendues"] if len(got) != len(exp) else []
    for i, (a, b) in enumerate(zip(exp, got)):
        if a != b:
            bad.append(f"seed {seed} ligne {i + 1}:\n      Python={a}\n      {target}={b}")
    return bad, len(exp), src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["cpp", "kotlin"], required=True)
    ap.add_argument("--seeds", type=int, default=5)
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
            (ROOT / "tests" / "fuzz_failure.py").write_text(src, encoding="utf-8")  # 1er programme fautif, pour le débogage
    for f in failures[:12]:
        print("  ÉCART", f)
    print(f"\n{total} lignes comparées, {len(failures)} écart(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

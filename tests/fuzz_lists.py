"""Fuzzer différentiel : compréhensions, génératrices, enumerate/zip/reversed, méthodes de liste, * et +.

  python tests/fuzz_lists.py --target cpp --seeds 20
  python tests/fuzz_lists.py --target kotlin --seeds 3
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


def body(seed, n):
    r = random.Random(seed)
    L = ["    xs: list[int] = [3, -1, 4, 1, 5]", "    ys: list[int] = [2, 7, 1]", "    ws: list[str] = [\"a\", \"bb\", \"ccc\"]",
         "    d: dict[int, int] = {}"]
    for k in range(n):
        v, w, i = r.randint(-4, 9), r.randint(-3, 5), r.randint(0, 3)
        op = r.randrange(34)
        if op == 0:
            L.append(f"    xs.append({v})")
        elif op == 1:
            L.append(f"    xs.insert({r.randint(-8, 8)}, {v})")
        elif op == 2:
            L.append(f"    xs.extend([{v}, {w}])" if r.random() < 0.6 else "    xs.extend(ys)")
        elif op == 3:
            L += ["    if len(xs) > 0:", f"        print(xs.pop(), len(xs))"]
        elif op == 4:
            L += ["    if len(xs) > 1:", f"        print(xs.pop(0), xs.pop(-1))"]
        elif op == 5:
            L.append(f"    print(xs.count({v}), {v} in xs, {v} not in ys)")
        elif op == 6:
            L += [f"    if {v} in xs:", f"        print(xs.index({v}))", f"        xs.remove({v})"]
        elif op == 7:
            L.append(f"    print([x * {v} for x in xs if x > {w}])")
        elif op == 8:
            L.append(f"    print({{x: x % 3 for x in xs}})")
        elif op == 9:
            L.append(f"    print(sum(x for x in xs if x % 2 == {i % 2}))")
        elif op == 10:
            L += ["    if len(xs) > 0:", f"        print(max(x + {v} for x in xs), min(x * {w} for x in xs))"]
        elif op == 11:
            L.append("    print([(i, x) for i, x in enumerate(xs)])")
        elif op == 12:
            L.append("    print([a + b for a, b in zip(xs, ys)])")
        elif op == 13:
            L.append("    print([x for x in reversed(xs)], list(reversed(ys)))")
        elif op == 14:
            L.append(f"    print(any(x > {v} for x in xs), all(x > {w} for x in xs), any([x == {i} for x in ys]))")
        elif op == 15:
            L.append(f"    print(xs * {i}, ys + [{v}], [{v}] * {i}, {i} * ws, \"ab\" * {i})")
        elif op == 16:
            L.append(f"    print([[a + b for b in range(a)] for a in range({i + 1})])")
        elif op == 17:
            L.append(f"    print(sorted([x % 5 for x in xs]), sorted(ws)[0])")
        elif op == 18:
            L += ["    for i, x in enumerate(xs, 2):", "        print(i, x)"]
        elif op == 19:
            L += ["    for a, b in zip(xs, ws):", "        print(a, b)"]
        elif op == 20:
            L += ["    for z in reversed(ys):", f"        print(z + {v})"]
        elif op == 21:
            L.append(f"    d[{i}] = {v}")
        elif op == 22:
            L.append("    print({k_: v_ + 1 for k_, v_ in d.items()}, [k_ for k_ in d], list(d.values()))")
        elif op == 23:
            L.append(f"    print([(a, b) for a in range({i}) for b in range(a, {i + 2}) if (a + b) % 2 == {w % 2}])")
        elif op == 24:
            L.append(f"    print([w_ + str({v}) for w_ in ws if len(w_) > {i % 3}])")
        elif op == 25:
            L.append("    xs = [x for x in xs if x != 4]")
        elif op == 26:
            L.append("    ys = [y_ * 2 for y_ in ys][:0] + [1, 2, 3]" if False else "    ys = [y_ + 1 for y_ in ys] + [0]")
        elif op == 27:
            L.append("    print(len([x for x in xs if x > 0]), xs, ys)")
        elif op == 28:
            L.append(f"    print(sum([x * y_ for x in xs for y_ in ys if x > y_]))")
        elif op == 29:
            L.append(f"    q = {v}")
            L.append("    print([q + x for x in range(3)], q)")
        elif op == 30:
            L.append("    print([(x, x * x) for x in ys])")
        elif op == 31:
            L.append("    print(list(enumerate(ws)), list(zip(ys, ws)))")
        elif op == 32:
            L.append(f"    print({{w_: len(w_) * {w} for w_ in ws}})")
        else:
            L.append(f"    print([c_ for c_ in [{v}, {w}, {i}] if c_ > 0] + [{v}])")
    L += ["    print(xs, ys, ws, d)"]
    return "\n".join(L) + "\n"


def program(seed, n):
    return "def main() -> None:\n" + body(seed, n) + "\n\nif __name__ == \"__main__\":\n    main()\n"


def run_seed(seed, n, target):
    src = program(seed, n)
    path = Path(tempfile.mkdtemp(prefix="fuzzl_")) / "prog.py"
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

"""Fuzzer différentiel : set d'entiers (ordre d'itération de CPython), deque, heapq, Counter/defaultdict.

  python tests/fuzz_sets.py --target cpp --seeds 20
  python tests/fuzz_sets.py --target kotlin --seeds 3
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

HEADER = '''import heapq
from collections import Counter, defaultdict, deque


def main() -> None:
    a: set[int] = set()
    b = {1, 2, 3}
    h: list[tuple[int, int]] = []
    dq: deque[int] = deque()
    cnt: Counter[int] = Counter()
    dd: defaultdict[int, list[int]] = defaultdict(list)
'''


def val(r):
    kind = r.randrange(6)
    if kind == 0:
        return r.randint(-5, 5)
    if kind == 1:
        return r.randint(0, 40)
    if kind == 2:
        return r.randint(0, 1000) * 8
    if kind == 3:
        return -r.randint(1, 300)
    if kind == 4:
        return r.randint(0, 3) * 2 ** r.randint(0, 40)
    return r.randint(-10 ** 6, 10 ** 6)


def body(seed, n):
    r = random.Random(seed)
    L = []
    for _ in range(n):
        v = val(r)
        op = r.randrange(26)
        if op <= 4:
            L.append(f"    a.add({v})")
        elif op == 5:
            L.append(f"    a.discard({v})")
        elif op == 6:
            L.append("    print(list(a), len(a))")
        elif op == 7:
            L.append(f"    b.add({v})")
        elif op == 8:
            L.append("    print(a | b, a & b, a - b, a ^ b)")
        elif op == 9:
            L.append("    print(list(b), a <= b, a >= b, a == b, a.isdisjoint(b))")
        elif op == 10:
            L.append("    if a:\n        print(a.pop(), len(a))")
        elif op == 11:
            L.append("    a |= b")
        elif op == 12:
            L.append("    a &= b")
        elif op == 13:
            L.append("    a -= b")
        elif op == 14:
            L.append("    a ^= b")
        elif op == 15:
            L.append(f"    a.update([{v}, {val(r)}, {val(r)}])")
        elif op == 16:
            L.append(f"    heapq.heappush(h, ({v % 17}, {val(r) % 100}))")
        elif op == 17:
            L.append("    if h:\n        print(heapq.heappop(h), len(h), h)")
        elif op == 18:
            L.append(f"    if {r.randrange(2)}:\n        dq.append({v})\n    else:\n        dq.appendleft({v})")
        elif op == 19:
            L.append("    if dq:\n        x = dq.pop() if " + str(r.randrange(2)) + " else dq.popleft()\n        print(x, len(dq), list(dq))")
        elif op == 20:
            L.append(f"    dq.rotate({r.randint(-4, 4)})")
        elif op == 21:
            L.append(f"    cnt[{v % 7}] += {r.randint(1, 3)}")
        elif op == 22:
            L.append("    print(cnt, cnt.most_common(3), cnt[99])")
        elif op == 23:
            L.append(f"    dd[{v % 5}].append({v})")
        elif op == 24:
            L.append("    print(dd, len(dd))")
        else:
            L.append("    a = set(sorted(a)[::2]) | {" + str(v) + "}")
    L.append("    print(list(a), list(b), len(dq), len(h))")
    return "\n".join(L) + "\n"


def program(seed, n):
    return HEADER + body(seed, n) + "\n\nif __name__ == \"__main__\":\n    main()\n"


def run_seed(seed, n, target):
    src = program(seed, n)
    path = Path(tempfile.mkdtemp(prefix="fuzzs_")) / "prog.py"
    path.write_text(src, encoding="utf-8")
    try:
        expected = python_output(path)
    except RuntimeError as ex:
        return [f"seed {seed}: le programme Python échoue : {str(ex)[:200]}"], 0, src
    try:
        code = transpile(src, target)
    except Unsupported as ex:
        return [f"seed {seed}: Unsupported : {ex}"], 0, src
    got, err = build_and_run(code, target)
    if err:
        return [f"seed {seed}: {err[:1500]}"], 0, src
    got, exp = got.replace("\r\n", "\n").splitlines(), expected.splitlines()
    bad = [f"seed {seed}: {len(got)} lignes obtenues, {len(exp)} attendues"] if len(got) != len(exp) else []
    for i, (x, y) in enumerate(zip(exp, got)):
        if x != y:
            bad.append(f"seed {seed} ligne {i + 1}:\n      Python={x}\n      {target}={y}")
    return bad, len(exp), src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["cpp", "kotlin"], required=True)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--n", type=int, default=90)
    a = ap.parse_args()
    total, failures = 0, []
    for seed in range(a.first, a.first + a.seeds):
        bad, n, src = run_seed(seed, a.n, a.target)
        total += n
        failures += bad
        print(f"seed {seed} : {n} lignes comparées, {len(bad)} écart(s)", flush=True)
        if bad and not (ROOT / "tests" / "fuzz_failure.py").exists():
            (ROOT / "tests" / "fuzz_failure.py").write_text(src, encoding="utf-8")
    for f in failures[:12]:
        print("  ÉCART", f)
    print(f"\n{total} lignes comparées, {len(failures)} écart(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

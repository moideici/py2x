"""Fuzzer différentiel : sorted/sort/min/max avec key=, reverse=, default= sur des listes pleines d'égalités (stabilité du tri).

  python tests/fuzz_sort.py --target cpp --seeds 20
  python tests/fuzz_sort.py --target kotlin --seeds 3
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

INT_KEYS = ["abs", "lambda x: x % 3", "lambda x: -x", "lambda x: (x % 2, -x)", "lambda x: x > 0", "lambda x: (x % 4, x % 3)",
            "lambda x: str(x)", "lambda x: abs(x) // 2", "None"]
STR_KEYS = ["len", "lambda s: s[-1:]", "lambda s: (len(s), s)", "str.lower", "lambda s: -len(s)", "lambda s: s.count('a')", "None"]
PAIR_KEYS = ["lambda p: p[1]", "lambda p: (p[1], p[0])", "lambda p: (-p[1], p[0])", "lambda p: p[0]", "lambda p: len(p[0]) + p[1]", "None"]


def body(seed, n):
    r = random.Random(seed)
    L = []

    def lst(kind):
        if kind == "int":
            return [r.randint(-6, 6) for _ in range(r.randint(0, 12))]
        if kind == "str":
            return ["".join(r.choice("abAB") for _ in range(r.randint(0, 4))) for _ in range(r.randint(0, 9))]
        return [(r.choice("abcab"), r.randint(0, 3)) for _ in range(r.randint(0, 10))]

    L.append("    ints: list[int] = []")
    L.append("    strs: list[str] = []")
    L.append("    pairs: list[tuple[str, int]] = []")
    for k in range(n):
        kind = r.choice(["int", "str", "pair"])
        name = {"int": "ints", "str": "strs", "pair": "pairs"}[kind]
        keys = {"int": INT_KEYS, "str": STR_KEYS, "pair": PAIR_KEYS}[kind]
        key = r.choice(keys)
        rev = r.choice(["", ", reverse=True", ", reverse=False"])
        kk = "" if key == "None" else f", key={key}"
        if key == "None" and not rev:
            kk = ""
        L.append(f"    {name} = {lst(kind)!r}")
        op = r.randrange(6)
        if op == 0:
            L.append(f"    print(sorted({name}{kk}{rev}))")
        elif op == 1:
            L.append(f"    {name}.sort({(kk + rev).lstrip(', ')})")
            L.append(f"    print({name})")
        elif op == 2:
            L.append(f"    print(min({name}{kk}, default={'0' if kind == 'int' else repr('') if kind == 'str' else repr(('z', 9))}))")
        elif op == 3:
            L.append(f"    print(max({name}{kk}, default={'0' if kind == 'int' else repr('') if kind == 'str' else repr(('z', 9))}))")
        elif op == 4:
            L.append(f"    print((sorted({name}{kk}{rev}), len({name})))")
        else:
            L.append(f"    print(sorted({name}{kk}), sorted({name}{kk}, reverse=True))")
    return "\n".join(L) + "\n"


def program(seed, n):
    return "def main() -> None:\n" + body(seed, n) + "\n\nif __name__ == \"__main__\":\n    main()\n"


def run_seed(seed, n, target):
    src = program(seed, n)
    path = Path(tempfile.mkdtemp(prefix="fuzzk_")) / "prog.py"
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
    prints = [l.strip() for l in src.splitlines() if l.strip().startswith("print(")]
    for i, (a, b) in enumerate(zip(exp, got)):
        if a != b:
            bad.append(f"seed {seed} ligne {i + 1}: {prints[i][:200] if i < len(prints) else ''}\n      Python={a}\n      {target}={b}")
    return bad, len(exp), src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["cpp", "kotlin"], required=True)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--n", type=int, default=40)
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

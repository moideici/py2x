"""Fuzzer différentiel : méthodes de chaînes, tranches, formatage (format specs aléatoires), arrondi, conversions.

Chaque ligne générée est d'abord évaluée par Python : on ne garde que celles qui ne lèvent pas d'exception, puis on compare
la sortie du programme complet (Python vs cible) ligne à ligne.

  python tests/fuzz_strings.py --target cpp --seeds 20
  python tests/fuzz_strings.py --target kotlin --seeds 3
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

ALPHA = "abcxyzXYZ019 ,.-_'\"\\\t"
SEPS = [",", " ", "ab", "--", "x", "0", "'", "bc"]
FLOATS = [0.0, 0.5, 1.5, 2.5, -0.5, 3.14159, -2.71828, 1.005, 2.675, 100.0, 1234567.891, 0.000123, 1e-7, 1e10, 123456789.0,
          0.1, 0.25, 99.995, 7.0, -7.5, 0.30000000000000004]
BIG_FLOATS = [1e22, 5e-324, 1e300, -1e22]
INTS = [0, 1, -1, 7, 42, -42, 255, 1000, -1000, 1234567, 65535, 2 ** 40, -(2 ** 33), 99999999]


def rstr(r, lo=0, hi=9):
    return "".join(r.choice(ALPHA) for _ in range(r.randint(lo, hi)))


def lit(s):
    return repr(s)


def rspec(r, kind):
    fill = r.choice(["", "", "", "*", "0", "-", "#", "_"])
    align = r.choice(["", "<", ">", "^", "="]) if fill == "" or r.random() < 0.7 else r.choice(["<", ">", "^"])
    if fill and not align:
        fill = ""
    sign = r.choice(["", "", "+", "-", " "])
    alt = r.choice(["", "", "#"])
    zero = r.choice(["", "", "", "0"])
    width = r.choice(["", "", "", "5", "8", "12", "3", "1"])
    group = r.choice(["", "", "", ",", "_"])
    prec = r.choice(["", "", ".0", ".1", ".2", ".3", ".6", ".10"])
    types = {"int": ["", "d", "b", "o", "x", "X", "n", "e", "f", "g", "%", "E", "F", "G"],
             "float": ["", "f", "e", "g", "%", "F", "E", "G"], "str": ["", "s"]}[kind]
    ty = r.choice(types)
    if kind == "str":
        group = sign = alt = ""
    return f"{fill}{align}{sign}{alt}{zero}{width}{group}{prec}{ty}"


def make_program(seed, n):
    r = random.Random(seed)
    env, lines = {}, []

    def assign(code):
        exec(code, env)
        lines.append("    " + code)

    def emit(expr):
        try:
            eval(expr, dict(env))
        except Exception:  # noqa: BLE001
            return False
        lines.append(f"    print({expr})")
        return True

    for i in range(3):
        assign(f"s{i} = {lit(rstr(r, 0, 12))}")
    assign(f"n0 = {r.choice(INTS)}")
    assign(f"f0 = {r.choice(FLOATS + BIG_FLOATS if r.random() < 0.15 else FLOATS)!r}")
    assign(f"xs: list[int] = [{', '.join(str(r.randint(-9, 9)) for _ in range(r.randint(0, 8)))}]")
    tries = 0
    while sum(1 for l in lines if l.lstrip().startswith("print(")) < n and tries < n * 6:
        tries += 1
        s = f"s{r.randint(0, 2)}"
        t = f"s{r.randint(0, 2)}"
        k = r.randrange(40)
        sep, ch = r.choice(SEPS), r.choice(ALPHA)
        lo, hi = r.choice(["", str(r.randint(-12, 12))]), r.choice(["", str(r.randint(-12, 12))])
        st = r.choice(["", "", "", "2", "-1", "-2", "3", "1"])
        sl = f"{lo}:{hi}" + (f":{st}" if st else "")
        if k == 0:
            e = f"{s}.upper(), {s}.lower(), {s}.title(), {s}.capitalize(), {s}.swapcase()"
        elif k == 1:
            e = f"{s}.strip({lit(rstr(r, 0, 3))}), {s}.lstrip({lit(rstr(r, 1, 3))}), {s}.rstrip({lit(rstr(r, 1, 3))}), {s}.strip()"
        elif k == 2:
            e = f"{s}.split(), {s}.split({lit(sep)}), {s}.split({lit(sep)}, {r.randint(0, 3)})"
        elif k == 3:
            e = f"{lit(sep)}.join({s}.split({lit(ch)})), {s}.splitlines()"
        elif k == 4:
            e = f"{s}.replace({lit(rstr(r, 1, 2))}, {lit(rstr(r, 0, 3))}), {s}.replace({lit(ch)}, {lit(sep)}, {r.randint(0, 3)}), {s}.replace('', {lit(ch)})"
        elif k == 5:
            e = f"{s}.find({lit(rstr(r, 1, 2))}), {s}.rfind({lit(ch)}), {s}.count({lit(rstr(r, 1, 2))}), {s}.count('')"
        elif k == 6:
            e = f"{s}.startswith({lit(rstr(r, 0, 2))}), {s}.endswith({lit(rstr(r, 0, 2))}), {s}.index({lit(ch)})"
        elif k == 7:
            e = f"{s}.isdigit(), {s}.isalpha(), {s}.isalnum(), {s}.isspace(), {s}.islower(), {s}.isupper()"
        elif k == 8:
            e = f"{s}.zfill({r.randint(0, 14)}), {s}.ljust({r.randint(0, 14)}, {lit(ch)}), {s}.rjust({r.randint(0, 14)}), {s}.center({r.randint(0, 14)}, {lit(ch)}), {s}.center({r.randint(0, 14)})"
        elif k == 9:
            e = f"{s}.removeprefix({lit(rstr(r, 0, 2))}), {s}.removesuffix({lit(rstr(r, 0, 2))})"
        elif k == 10:
            e = f"{s}[{sl}], {t}[{sl}], len({s}[{sl}])"
        elif k == 11:
            e = f"xs[{sl}], sum(xs[{sl}]), xs[{sl}][::-1]"
        elif k == 12:
            e = f"repr({s}), repr({s}[{sl}]), [{s}, {t}]"
        elif k == 13:
            e = f"ord({lit(ch)}), chr({r.randint(32, 126)}), int({lit(str(r.choice(INTS)))}), float({lit(repr(r.choice(FLOATS)))}), int(' +{abs(r.choice(INTS))} ')"
        elif k == 14:
            e = f"format(n0, {lit(rspec(r, 'int'))}), format(f0, {lit(rspec(r, 'float'))}), format({s}, {lit(rspec(r, 'str'))})"
        elif k == 15:
            e = f"f'{{n0:{rspec(r, 'int')}}}|{{f0:{rspec(r, 'float')}}}|{{{s}:{rspec(r, 'str')}}}'"
        elif k == 16:
            e = f"round({r.choice(FLOATS)!r}), round({r.choice(FLOATS)!r}, {r.randint(0, 4)}), round(f0) if abs(f0) < 1e18 else 0, round(f0, {r.randint(0, 3)})"
        elif k == 17:
            e = f"divmod({r.choice(INTS)}, {r.choice([x for x in INTS if x])}), pow({r.randint(-9, 9)}, {r.randint(0, 9)}), pow({r.randint(2, 99)}, {r.randint(0, 30)}, {r.randint(1, 1000)})"
        elif k == 18:
            e = f"bin(n0), hex(n0), oct(n0), n0.bit_length(), abs(n0).bit_count()"
        elif k == 19:
            e = f"'%d|%5d|%-6d|%06d|%+d|%x|%o' % ({r.choice(INTS)}, {r.choice(INTS)}, {r.choice(INTS)}, {r.choice(INTS)}, {r.choice(INTS)}, abs(n0), abs(n0))"
        elif k == 20:
            e = f"'%s|%10s|%-10s|%.3s' % ({lit(rstr(r))}, {s}, {t}, {s})"
        elif k == 21:
            e = f"'%f|%.2f|%8.3f|%e|%g|%.0f' % ({', '.join([repr(r.choice(FLOATS)) for _ in range(6)])})"
        elif k == 22:
            e = f"'{{}}-{{:>6}}-{{:.1f}}'.format({s}, {r.choice(INTS)}, {r.choice(FLOATS)!r}), '{{0}}{{1}}{{0}}'.format({s}, {t})"
        elif k == 23:
            e = f"[c for c in {s}], sorted({s}), list({s}[:3]), max({s}) if {s} else '', min({s}) if {s} else ''"
        elif k == 24:
            e = f"{s} + {t}, {s} * {r.randint(-1, 3)}, {s} < {t}, {s} == {t}, {s} in {t}, {s} not in {t}"
        elif k == 25:
            e = f"[(i, c) for i, c in enumerate({s})], list(zip({s}, {t}))"
        elif k == 26:
            e = f"f'{{f0!r}} {{s0!r}} {{n0!s}} {{n0!r:>8}} {{s1:{rspec(r, 'str')}}}'"
        elif k == 27:
            e = f"f'{{{r.choice(FLOATS)!r}:{rspec(r, 'float')}}}', f'{{{r.choice(INTS)}:{rspec(r, 'int')}}}'"
        elif k == 28:
            e = f"{s}.split({lit(sep)})[{r.randint(-2, 2)}] if len({s}.split({lit(sep)})) > 2 else 'short'"
        elif k == 29:
            e = f"int(f0) if abs(f0) < 1e18 else 0, float(n0), str(f0), str(n0), bool({s}), bool(n0)"
        else:
            e = f"{s}[{r.randint(-14, 14)}] if {r.randint(0, 1)} and len({s}) > 0 else {t}"
        emit(e)
    # opérations de mutation de liste par tranche
    for _ in range(4):
        a = r.choice(["", str(r.randint(-6, 6))])
        b = r.choice(["", str(r.randint(-6, 6))])
        code = r.choice([f"xs[{a}:{b}] = [{r.randint(0, 9)}, {r.randint(0, 9)}]", f"del xs[{a}:{b}]", f"xs[::2] = xs[::2]", "xs.append(1)"])
        try:
            exec(code, env)
        except Exception:  # noqa: BLE001
            continue
        lines.append("    " + code)
        lines.append("    print(xs)")
    return "def main() -> None:\n" + "\n".join(lines) + "\n\n\nif __name__ == \"__main__\":\n    main()\n"


def run_seed(seed, n, target):
    src = make_program(seed, n)
    path = Path(tempfile.mkdtemp(prefix="fuzzs_")) / "prog.py"
    path.write_text(src, encoding="utf-8")
    expected = python_output(path)
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
            bad.append(f"seed {seed} ligne {i + 1}: {prints[i][:230] if i < len(prints) else ''}\n      Python={a}\n      {target}={b}")
    return bad, len(exp), src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["cpp", "kotlin"], required=True)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--n", type=int, default=80)
    a = ap.parse_args()
    total, failures = 0, []
    for seed in range(a.first, a.first + a.seeds):
        bad, n, src = run_seed(seed, a.n, a.target)
        total += n
        failures += bad
        print(f"seed {seed} : {n} lignes comparées, {len(bad)} écart(s)", flush=True)
        if bad and not (ROOT / "tests" / "fuzz_failure.py").exists():
            (ROOT / "tests" / "fuzz_failure.py").write_text(src, encoding="utf-8")
    for f in failures[:20]:
        print("  ÉCART", f)
    print(f"\n{total} lignes comparées, {len(failures)} écart(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

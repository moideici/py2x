"""Mesure d'utilisabilité : convertit chaque programme de corpus/ vers C++ et Kotlin, compile, compare la sortie à Python.

  python corpus_report.py                    # conversion seule (rapide) : quels programmes sont refusés, et pourquoi
  python corpus_report.py --compile cpp      # + compile/exécute/compare en C++
  python corpus_report.py --compile cpp,kotlin
  python corpus_report.py --dir corpus2      # un autre jeu de programmes
"""
import argparse
import collections
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from py2x import Unsupported, transpile  # noqa: E402
from py2x.verify import build_and_run, python_output  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="corpus")
    ap.add_argument("--compile", default="", help="cpp, kotlin ou cpp,kotlin")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    targets = [t for t in a.compile.split(",") if t]
    files = sorted((ROOT / a.dir).glob("*.py"))
    if a.only:
        files = [f for f in files if f.stem in a.only]
    status = {}
    reasons = collections.Counter()
    for f in files:
        src = f.read_text(encoding="utf-8")
        try:
            expected = python_output(f)
        except Exception as e:  # noqa: BLE001
            print(f"{f.stem:22s} !! le programme Python lui-même échoue : {str(e)[:120]}")
            continue
        row = {}
        for t in ("cpp", "kotlin"):
            try:
                code = transpile(src, t)
            except Unsupported as e:
                msg = str(e)
                row[t] = ("refus", msg)
                reasons[re.sub(r"^ligne \d+ : ", "", msg)[:90]] += 1
                continue
            except Exception as e:  # noqa: BLE001  (bug du convertisseur)
                row[t] = ("BUG", f"{type(e).__name__}: {e}")
                reasons[f"BUG {type(e).__name__}: {str(e)[:70]}"] += 1
                continue
            if t in targets:
                got, err = build_and_run(code, t)
                if err:
                    row[t] = ("compil", err.replace("\n", " ")[:160])
                elif got.replace("\r\n", "\n") != expected:
                    exp_l, got_l = expected.splitlines(), got.replace("\r\n", "\n").splitlines()
                    diff = next(((i + 1, x, y) for i, (x, y) in enumerate(zip(exp_l, got_l)) if x != y), None)
                    row[t] = ("DIFF", f"ligne {diff[0]} : Python={diff[1]!r} {t}={diff[2]!r}" if diff else "nombre de lignes différent")
                else:
                    row[t] = ("OK", "")
            else:
                row[t] = ("converti", "")
        status[f.stem] = row
        c, k = row["cpp"], row["kotlin"]
        line = f"{f.stem:22s} cpp:{c[0]:8s} kotlin:{k[0]:8s}"
        first_bad = c if c[0] not in ("OK", "converti") else k
        if first_bad[0] not in ("OK", "converti"):
            line += " | " + first_bad[1][:150]
        print(line)
    n = len(status)
    ok = {t: sum(1 for r in status.values() if r[t][0] in ("OK", "converti")) for t in ("cpp", "kotlin")}
    label = "OK (identique à Python)" if targets else "convertis"
    print(f"\n{n} programmes : cpp {ok['cpp']}/{n} {label}, kotlin {ok['kotlin']}/{n}")
    if reasons:
        print("\nObstacles les plus fréquents (premier obstacle par programme et par cible) :")
        for r, c in reasons.most_common(25):
            print(f"  {c:3d}  {r}")


if __name__ == "__main__":
    main()

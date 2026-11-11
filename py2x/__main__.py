import argparse
import sys
from pathlib import Path

from . import TARGETS, Unsupported, transpile


def verify(path, targets, strict):
    """Convertit, compile et exécute dans chaque langage ; compare la sortie à celle de Python. Code de sortie 1 en cas d'écart."""
    from .verify import build_and_run, python_output
    source = Path(path).read_text(encoding="utf-8")
    expected = python_output(path)
    ok = True
    for t in targets:
        try:
            code = transpile(source, t, strict=strict)
        except Unsupported as e:
            print(f"{t:7} REFUS : {e}")
            ok = False
            continue
        got, err = build_and_run(code, t)
        if err:
            print(f"{t:7} ERREUR DE COMPILATION : {err[:400]}")
            ok = False
        elif got.replace("\r\n", "\n") != expected.replace("\r\n", "\n"):
            exp_lines, got_lines = expected.splitlines(), got.replace("\r\n", "\n").splitlines()
            first = next((i for i, (a, b) in enumerate(zip(exp_lines, got_lines)) if a != b), min(len(exp_lines), len(got_lines)))
            print(f"{t:7} ÉCART à la ligne {first + 1} : Python={exp_lines[first] if first < len(exp_lines) else '<fin>'!r} "
                  f"{t}={got_lines[first] if first < len(got_lines) else '<fin>'!r}")
            ok = False
        else:
            print(f"{t:7} OK : sortie identique à Python ({len(exp_lines := expected.splitlines())} lignes)")
    return ok


def main():
    ap = argparse.ArgumentParser(prog="py2x", description="Python typé -> C++ / Kotlin")
    ap.add_argument("file", nargs="?", help="fichier Python source")
    ap.add_argument("--to", choices=sorted(TARGETS), help="langage cible")
    ap.add_argument("-o", "--output", help="fichier de sortie (défaut : stdout)")
    ap.add_argument("--strict", action="store_true",
                    help="refuse (au lieu d'avertir) un int utilisé là où un float est annoté : Python garderait un int")
    ap.add_argument("--package", help="Kotlin : déclaration `package` du fichier généré")
    ap.add_argument("--no-runtime", action="store_true", help="Kotlin : n'émet pas le runtime (à générer une fois avec --runtime-only)")
    ap.add_argument("--runtime-only", action="store_true", help="Kotlin : émet seulement le runtime (PyRuntime.kt)")
    ap.add_argument("--camel", action="store_true", help="Kotlin : identifiants en camelCase (get_value -> getValue)")
    ap.add_argument("--verify", metavar="CIBLES", nargs="?", const="cpp,kotlin",
                    help="compile et exécute le code généré (cpp,kotlin) et compare sa sortie à celle de Python")
    a = ap.parse_args()
    if a.runtime_only:
        from .emit_kotlin import KotlinEmitter
        code = KotlinEmitter.runtime_source(a.package)
        if a.output:
            Path(a.output).write_text(code, encoding="utf-8")
        else:
            sys.stdout.write(code)
        return
    if a.file is None:
        ap.error("fichier source requis")
    if a.verify is not None:
        ok = verify(a.file, [t for t in a.verify.split(",") if t], a.strict)
        sys.exit(0 if ok else 1)
    if not a.to:
        ap.error("--to est obligatoire (sauf avec --verify)")
    warnings = []
    try:
        code = transpile(Path(a.file).read_text(encoding="utf-8"), a.to, strict=a.strict, warnings=warnings,
                         runtime=not a.no_runtime, package=a.package, camel=a.camel)
    except Unsupported as e:
        print(f"{a.file}: non supporté : {e}", file=sys.stderr)
        sys.exit(2)
    for w in warnings:
        print(f"{a.file}: avertissement : {w}", file=sys.stderr)
    if a.output:
        Path(a.output).write_text(code, encoding="utf-8")
    else:
        sys.stdout.write(code)


if __name__ == "__main__":
    main()

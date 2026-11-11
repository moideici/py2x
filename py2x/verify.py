"""Vérification de bout en bout : exécute le programme Python, exécute le code généré, compare les sorties."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import transpile

LOW_PRIORITY = 0x00004000 if sys.platform == "win32" else 0  # BELOW_NORMAL_PRIORITY_CLASS : ne gêne pas un jeu ouvert
SCOOP = Path.home() / "scoop"


def tool(name):
    p = shutil.which(name)
    if p:
        return p
    for d in (SCOOP / "shims", SCOOP / "apps" / "mingw" / "current" / "bin"):
        for ext in (".cmd", ".bat", ".exe", ""):
            if (d / (name + ext)).exists():
                return str(d / (name + ext))
    raise FileNotFoundError(name)


def run(cmd, cwd=None, timeout=180):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, creationflags=LOW_PRIORITY)
    return p.returncode, p.stdout, p.stderr


def python_output(path):
    rc, out, err = run([sys.executable, str(path)], timeout=60)
    if rc != 0:
        raise RuntimeError(f"le programme Python échoue : {err[-300:]}")
    return out


def build_and_run(code, target, work=None):
    """Compile le code généré puis l'exécute. Renvoie (stdout, message d'erreur de compilation ou '')."""
    work = Path(work or tempfile.mkdtemp(prefix="py2x_"))
    work.mkdir(parents=True, exist_ok=True)
    try:
        if target == "cpp":
            (work / "prog.cpp").write_text(code, encoding="utf-8")
            rc, out, err = run([tool("g++"), "-std=c++20", "-O1", "prog.cpp", "-o", "prog.exe"], work)
            if rc != 0:
                return "", (out + err)[:1500]
            rc, out, err = run([str(work / "prog.exe")], work, 30)
        else:
            (work / "main.kt").write_text(code, encoding="utf-8")
            rc, out, err = run([tool("kotlinc"), "-nowarn", "main.kt", "-include-runtime", "-d", "prog.jar"], work, 300)
            if rc != 0:
                return "", (out + err)[:1500]
            rc, out, err = run([tool("java"), "-cp", "prog.jar", "MainKt"], work, 30)
        if rc != 0:
            return out, f"exécution échouée (code {rc}) : {err[-300:]}"
        return out, ""
    finally:
        shutil.rmtree(work, ignore_errors=True)


def check(path, target):
    """Renvoie (ok, détail) pour un fichier Python et une cible."""
    path = Path(path)
    expected = python_output(path)
    code = transpile(path.read_text(encoding="utf-8"), target)
    got, err = build_and_run(code, target)
    if err:
        return False, err
    if got.replace("\r\n", "\n") != expected:
        return False, f"sortie différente.\n--- attendu (Python) ---\n{expected}\n--- obtenu ({target}) ---\n{got}"
    return True, ""

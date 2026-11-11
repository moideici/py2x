# Utilisation

## Ligne de commande

```bash
python -m py2x FICHIER.py --to {cpp,kotlin} [options]
python -m py2x FICHIER.py --verify [CIBLES]
python -m py2x --runtime-only [--package PKG] [-o PyRuntime.kt]
```

Après `pip install .` la commande `py2x` est aussi disponible (`py2x FICHIER.py --to cpp`).

| Option | Effet |
|---|---|
| `--to cpp` / `--to kotlin` | langage cible (obligatoire sauf avec `--verify`) |
| `-o`, `--output FICHIER` | écrit dans un fichier au lieu de stdout |
| `--strict` | refuse (au lieu d'avertir) un `int` utilisé là où un `float` est annoté : Python garderait un `int` (`x: float = 3` affiche `3`) |
| `--verify [cpp,kotlin]` | convertit, **compile** (basse priorité), exécute, compare la sortie à celle de Python ; défaut : les deux cibles |
| `--package PKG` | Kotlin : ajoute `package PKG` en tête du fichier généré |
| `--no-runtime` | Kotlin : n'émet pas le runtime (à générer une fois avec `--runtime-only`) |
| `--runtime-only` | Kotlin : n'émet que le runtime (`PyRuntime.kt`) |
| `--camel` | Kotlin : identifiants en camelCase (`get_value` → `getValue`) |

### Codes de sortie

| Code | Signification |
|---|---|
| 0 | conversion réussie (ou `--verify` : sorties identiques) |
| 1 | `--verify` : écart de sortie, erreur de compilation ou refus |
| 2 | construction non supportée (message `fichier: non supporté : ligne N : …` sur stderr) |

Les avertissements (par exemple l'`int` converti en `float`) vont sur stderr sans changer le code de sortie.

### Exemples

```bash
# C++ : un seul fichier autonome (runtime inclus)
python -m py2x examples/classes.py --to cpp -o classes.cpp
g++ -std=c++20 -O2 classes.cpp -o classes

# Kotlin : runtime à part, partagé par plusieurs programmes
python -m py2x --runtime-only --package app.generated -o PyRuntime.kt
python -m py2x examples/classes.py --to kotlin --no-runtime --package app.generated --camel -o Classes.kt

# Vérification sur une cible seulement
python -m py2x examples/sorting.py --verify cpp
```

## API Python

```python
from py2x import transpile, Unsupported

source = open("prog.py", encoding="utf-8").read()
warnings = []
try:
    cpp = transpile(source, "cpp", strict=False, warnings=warnings)
    kt = transpile(source, "kotlin", package="app", runtime=False, camel=True)
except Unsupported as e:
    print(e)          # "ligne 12 : ..."
```

| Fonction | Rôle |
|---|---|
| `transpile(source, target, strict=False, warnings=None, runtime=True, package=None, camel=False)` | source Python → code `"cpp"` ou `"kotlin"` ; lève `Unsupported` hors du sous-ensemble ; `runtime`, `package`, `camel` ne concernent que Kotlin |
| `to_ir(source, strict=False, warnings=None)` | source → IR typée (voir [ARCHITECTURE.md](ARCHITECTURE.md)) |
| `py2x.verify.check(path, target)` | `(ok, détail)` : compile, exécute et compare à Python |
| `py2x.verify.build_and_run(code, target)` | compile et exécute du code généré, renvoie `(stdout, erreur)` |

## Outils requis pour compiler

`py2x.verify` cherche `g++`, `kotlinc` et `java` dans le PATH, puis dans `~/scoop/shims` et `~/scoop/apps/mingw/current/bin`.
C++ : `g++ -std=c++20 -O1`. Kotlin : `kotlinc -nowarn … -include-runtime`, exécuté via `java -cp prog.jar MainKt`.
Le code de niveau module est accepté (constantes, alias de types, `main()`) ; un seul bloc `if __name__ == "__main__":` est permis.

## Comportement à l'exécution du code généré

- Exception non rattrapée : message sur stderr, code de sortie 1 (comme Python).
- Erreurs d'exécution (division par zéro, indice, clé, `int("x")`, `math.sqrt(-1)`…) : vraies exceptions rattrapables, mêmes **messages** que Python.
- Dépassement d'entier 64 bits : `OverflowError` (Python aurait un entier non borné).

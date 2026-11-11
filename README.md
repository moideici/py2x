# py2x : Python typé → C++20 / Kotlin

Convertisseur source-à-source. Un programme Python écrit dans un **sous-ensemble typé** est converti en C++20 ou en Kotlin/JVM,
et le programme généré produit **exactement la même sortie** que Python (octet pour octet).

```
ast Python  →  IR typée neutre  →  émetteur C++20
                                →  émetteur Kotlin
```

Ce qui n'est pas supporté est refusé avec une **erreur explicite et un numéro de ligne** (code de sortie 2) : jamais de code faux en silence.

## Démarrage rapide

Pré-requis : Python ≥ 3.11 (aucune dépendance). Pour `--verify` : `g++` (C++20) et `kotlinc` + `java` dans le PATH.

```bash
git clone https://github.com/moideici/py2x.git
cd py2x
python -m py2x examples/fib.py --to cpp                 # C++ sur stdout
python -m py2x examples/fib.py --to kotlin -o Fib.kt    # Kotlin dans un fichier
python -m py2x examples/fib.py --verify                 # convertit, compile, exécute, compare avec Python
```

Exemple de programme accepté (`examples/fib.py`) :

```python
def fib(n: int) -> int:
    a: int = 0
    b: int = 1
    for _ in range(n):
        a, b = b, a + b
    return a

def main() -> None:
    for i in range(10):
        print(i, fib(i))
```

Les fonctions doivent être **annotées** (paramètres et retour, `-> None` inclus) ; les variables locales sont inférées.

## Documentation

| Document | Contenu |
|---|---|
| [docs/USAGE.md](docs/USAGE.md) | Ligne de commande, options, API Python, génération Kotlin avec/sans runtime |
| [docs/SUPPORTED.md](docs/SUPPORTED.md) | Sous-ensemble Python supporté, bibliothèque standard, limites volontaires |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Frontend, IR, émetteurs, runtimes, comment ajouter un langage |
| [docs/TESTING.md](docs/TESTING.md) | Tests unitaires, corpus, fuzzers différentiels, CI |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Ajouter une fonctionnalité sans casser la garantie |
| [docs/README.md](docs/README.md) | Index et statut des documents |

## Garantie

Chaque programme de `examples/`, `corpus/`, `corpus2/` et `corpus3/` (≈ 60 programmes réalistes) est converti, compilé, exécuté, et sa sortie est
identique à celle de Python, en C++ comme en Kotlin. Huit fuzzers différentiels comparent des milliers de programmes aléatoires ligne à ligne avec Python.

## Limites principales

`int` 64 bits (un dépassement lève `OverflowError`), `str` ASCII, annotations obligatoires sur les fonctions, pas de `with`/`async`/décorateurs
utilisateur/héritage multiple, pas de `re`/`json`/`datetime`/fichiers. Liste complète : [docs/SUPPORTED.md](docs/SUPPORTED.md).

## Origine

Extrait le 2026-11-11 de `ia/transpiler` (dossier local `ia`). Les démonstrations qui utilisent py2x (TaskDesk, MindMap) et le socle C++
`cpp_base` restent dans `ia`.

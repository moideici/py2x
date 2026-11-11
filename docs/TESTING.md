# Tests

Le critère de qualité est unique : **la sortie du programme généré est identique à celle de Python**.

## Niveaux

| Niveau | Commande | Durée | Pré-requis |
|---|---|---|---|
| Rapide : conversion de tous les exemples + messages de refus | `python -m unittest discover -s tests` | < 1 s | Python |
| Idiomes : 100+ petits programmes acceptés/refusés | `python tests/idioms.py` | rapide | Python |
| Complet : compile et compare les `examples/` | `PY2X_COMPILE=cpp,kotlin python -m unittest discover -s tests` | ≈ 5 min | `g++`, `kotlinc`, `java` |
| C++ seul / Kotlin seul | `PY2X_COMPILE=cpp …` / `PY2X_COMPILE=kotlin …` | Kotlin est plus lent | idem |
| Corpus réalistes | `python corpus_report.py --dir corpus3 --compile cpp,kotlin` | minutes | idem |
| Fuzzers différentiels | `python tests/fuzz_expr.py --target cpp --seeds 20` | minutes | idem |

## Corpus

`corpus/`, `corpus2/`, `corpus3/` : programmes écrits **indépendamment du convertisseur** (les deuxième et troisième *après* les fonctionnalités
des précédents, pour mesurer la généralisation). `corpus_report.py --dir DOSSIER` convertit chaque programme, le compile et affiche
accepté / refusé / écart.

## Fuzzers différentiels (`tests/fuzz_*.py`)

Chacun génère des programmes aléatoires, les exécute en Python et dans la cible, et compare ligne à ligne :

| Fuzzer | Cible testée |
|---|---|
| `fuzz_expr` | expressions arithmétiques, bit à bit, comparaisons |
| `fuzz_data` | formats, conversions, structures de données |
| `fuzz_strings` | méthodes de `str`, formats |
| `fuzz_sort` | tris stables avec `key` |
| `fuzz_lists`, `fuzz_alias` | listes, tranches, alias et partage de poignées |
| `fuzz_classes` | classes, héritage, méthodes spéciales |
| `fuzz_optional` | `Optional` et affinage de type |
| `fuzz_sets` | `set` et ordre d'itération (oracle : `emu_set.py`) |
| `fuzz_exc` | exceptions et messages |

Options : `--target {cpp,kotlin}`, `--seeds N` (voir `--help` de chaque fuzzer). En cas d'écart, le programme fautif est affiché : le copier dans
`corpus*/` ou `tests/test_py2x.py` comme test de non-régression.

## Intégration continue

`.github/workflows/tests.yml` : à chaque push et PR, tests rapides + idiomes, et les `examples/` compilés en C++ (`PY2X_COMPILE=cpp`).
Kotlin n'est pas compilé en CI (lent) : le lancer en local avant de fusionner un changement d'émetteur ou de runtime Kotlin.

# Contribuer

## Avant de commencer

1. `python -m unittest discover -s tests` doit passer (58 tests).
2. Lire [ARCHITECTURE.md](ARCHITECTURE.md) : le frontend est neutre, les langages ne se mélangent pas.

## Ajouter une construction Python

1. **Frontend** : ajouter le cas dans le bon `*_fe.py` (méthode `s_<Node>` pour une instruction, `e_<Node>` pour une expression dans `frontend.py`).
   Les constructions inconnues lèvent déjà `Unsupported` avec le numéro de ligne : transformer ce refus en support, ou le laisser s'il est voulu.
2. **IR** : réutiliser un nœud existant ; n'en créer un (dans `ir.py`) que si les deux émetteurs ont besoin d'une forme nouvelle.
3. **Émetteurs** : traiter le nœud dans `emit_cpp.py` **et** `emit_kotlin.py`, plus le runtime si besoin (`runtime_cpp*.py`, `runtime_kt*.py`).
4. **Bibliothèque** : une nouvelle fonction de la stdlib va dans `std_fe.py`/`lib.py` avec ses deux gabarits (`cpp`, `kt`).
5. **Tests** : un exemple dans `examples/` (il est converti et comparé automatiquement), un cas dans `tests/test_py2x.py` ou `tests/idioms.py`,
   et si la sémantique est subtile (ordre, arrondi, alias), le fuzzer correspondant.
6. **Docs** : mettre à jour [SUPPORTED.md](SUPPORTED.md) (supporté ET limites).

## Règles d'or

- **Jamais de code faux en silence** : si la sémantique ne peut pas être reproduite exactement, refuser avec un message clair.
- **Même sortie que Python** : vérifier avec `--verify` en C++ *et* Kotlin avant de commit.
- Messages utilisateur en français, avec le numéro de ligne (`Unsupported(msg, node)`).
- Pas de dépendance externe : le projet ne repose que sur la bibliothèque standard de Python.

## Commits

Messages clairs au présent. Commit de docs seule : ajouter `[skip ci]`.

# Architecture

```
source Python
   │  ast.parse
   ▼
Frontend (py2x/frontend.py + *_fe.py)      inférence de types, résolution des noms, refus explicites
   │
   ▼
IR typée neutre (py2x/ir.py, types.py)     plus de sucre syntaxique, conversions explicites
   │
   ├──► CppEmitter    (emit_cpp.py)    + runtime_cpp*.py      → C++20 (un fichier autonome)
   └──► KotlinEmitter (emit_kotlin.py) + runtime_kt*.py       → Kotlin/JVM
```

Principe : **le frontend ne connaît aucun langage cible**. Ajouter un langage = écrire un émetteur + son runtime.

## Frontend

| Fichier | Rôle |
|---|---|
| `frontend.py` | cœur : instructions, expressions, fonctions, fermetures, générateurs, narrowing `Optional`/`isinstance` |
| `builtins_fe.py` | fonctions natives (`len`, `range`, `sorted`, `print`, `min/max`, `int()`, `str()`…) et méthodes de `str`/`int` |
| `coll_fe.py` | `list`, `dict`, `set`, `deque`, compréhensions, tranches |
| `classes_fe.py` | classes, dataclasses, `NamedTuple`, `@property`, méthodes spéciales, exceptions utilisateur |
| `enum_fe.py` | `Enum` |
| `std_fe.py` | bibliothèque standard (`math`, `itertools`, `bisect`, `heapq`, `random`, `functools`, `collections`) |
| `lib.py`, `names.py`, `excs.py` | table des fonctions de bibliothèque (`Fn` : gabarits C++ et Kotlin), noms réservés/mangling, hiérarchie d'exceptions |
| `errors.py` | `Unsupported` : l'erreur de refus, avec le numéro de ligne du nœud AST fautif |

### Inférence en deux phases (`to_ir`, `__init__.py`)

Les littéraux vides (`[]`, `{}`, `list()`, `set()`, `deque()`, `defaultdict`…) n'ont pas de type visible. `to_ir` lance donc jusqu'à 6 passes
**à blanc** (`Frontend(dry=True)`) qui collectent des indices (`append`, valeur de retour, argument d'appel, affectation) jusqu'à stabilité, puis
une vraie passe qui s'en sert. Un type jamais déterminé est un refus.

### Choix de conception visibles dans l'IR

- conversions `int → float` insérées (`Cast`) ; comparaisons chaînées décomposées ; `x += 1` → affectation ;
- variables déclarées dans des blocs imbriqués **hissées** (hoisting) pour les langages à portée de bloc ;
- listes, dicts et sets sont des **poignées partagées** (alias Python reproduit) ; objets par référence ;
- `Optional[T]` explicite, avec affinage de type après `is None` / `isinstance`.

## IR (`ir.py`, `types.py`)

Dataclasses : expressions (`Const`, `Var`, `BinOp`, `Cmp`, `BoolOp`, `Unary`, `Ternary`, `Cast`, `Call`, `MethodCall`, `Index`, `ListLit`, `DictLit`,
`TupleLit`, `Attr`, `New`, `NoneOf`…) et instructions, toutes **typées** (`Type` dans `types.py` : `int`, `float`, `bool`, `str`, `list_of`, `dict_of`,
`set_of`, `deque_of`, `tuple_of`, `optional_of`, `func_of`, `gen_of`, `class_of`…). Un émetteur traduit nœud par nœud sans rien inférer.

## Émetteurs et runtimes

| Cible | Émetteur | Runtime |
|---|---|---|
| C++20 | `emit_cpp.py` | `runtime_cpp.py` (base), `runtime_cpp_coll.py` (`PyList`/`PyDict`/`PySet`…), `runtime_cpp_str.py` (chaînes, `repr`), `runtime_cpp_fmt.py` (mini-langage de format), `runtime_cpp_exc.py` (exceptions) ; générateurs par coroutines C++20 |
| Kotlin | `emit_kotlin.py` | `runtime_kt_coll.py`, `runtime_kt_str.py`, `runtime_kt_exc.py` ; `KotlinEmitter.runtime_source()` produit `PyRuntime.kt` |

Les runtimes sont des **chaînes de code** embarquées dans des modules Python, concaténées à la sortie (C++ : un seul `.cpp` autonome).

### Fidélité à CPython

- `random_prelude.py` : **Mersenne Twister de CPython** écrit en Python typé, transpilé comme du code utilisateur (donc même suite que `random.seed(42)`).
- Ordre d'itération des `set` d'entiers : table de hachage de CPython émulée (`tests/emu_set.py` sert d'oracle).
- Division/modulo vers le bas, `repr` exact des flottants, tri stable, ordre d'insertion des `dict`, messages d'exception identiques.

## Vérification (`verify.py`)

`check(path, target)` exécute le programme Python, convertit, compile (`g++ -std=c++20 -O1` ou `kotlinc`), exécute et compare les sorties.
Voir [TESTING.md](TESTING.md).

## Ajouter un langage cible

1. Écrire `emit_<lang>.py` avec une classe d'émetteur ayant `emit(module)` qui prend l'IR et renvoie le code source.
2. Écrire le runtime du langage (collections à poignées partagées, exceptions Python, formats, `repr`, tri stable, Mersenne Twister via `random_prelude`).
3. L'enregistrer dans `TARGETS` (`py2x/__init__.py`) ; ajouter les gabarits correspondants dans les entrées `Fn` de `lib.py`.
4. Étendre `verify.build_and_run` pour compiler/exécuter la cible ; les tests de corpus et fuzzers prennent la cible via `--target` / `PY2X_COMPILE`.
5. Le critère d'acceptation est le même que pour C++ et Kotlin : corpus et fuzzers identiques à Python.

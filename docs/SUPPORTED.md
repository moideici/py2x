# Sous-ensemble Python supporté

py2x accepte un sous-ensemble **typé et statique** de Python 3.11. Tout le reste est refusé avec `non supporté : ligne N : …` (code de sortie 2).
Pour savoir si un idiome passe, le plus rapide : `python tests/idioms.py` (100+ petits idiomes acceptés/refusés) ou essayer `--to cpp`.

Règles de base : les **fonctions et méthodes sont entièrement annotées** (`-> None` si rien n'est retourné) ; les variables locales sont inférées ;
une variable ne change jamais de type.

## Ce qui est supporté

**Types** : `int`, `float`, `bool`, `str`, `list[T]`, `dict[K, V]`, `tuple[A, B]`, `tuple[T, ...]`, `set[T]`, `deque[T]`, `Optional[T]` / `T | None`,
`Callable[[A], R]`, `Iterator[T]`, classes, dataclasses, `Enum`, alias de types (`Grid = list[list[int]]`).

**Instructions** : fonctions (valeurs par défaut, arguments nommés, `*args`), `if/elif/else`, `while`, `for` (range, listes, dict, sets, générateurs,
dépaquetage `for a, (b, c) in …`), `for/else`, `while/else`, `break/continue`, `return`, `global`, `nonlocal`, fonctions imbriquées et fermetures
(y compris retournées), `assert`, `raise [… from …]`, `try/except/else/finally` (types multiples, `as e`, `raise` seul), dépaquetage étoilé
`a, *rest = xs`, affectations multiples/échanges, `del`, `print(..., sep=, end=, file=sys.stderr)`, `print(*xs)`.

**Expressions** : arithmétique et bit à bit (division entière/modulo/puissance de Python), comparaisons chaînées, `and/or/not`, `in`, `is None`,
`x if c else y`, f-strings (formats imbriqués, `!r`), `%` et `str.format`, tranches `xs[a:b:c]`, compréhensions de liste/dict/set (imbriquées,
avec conditions), expressions génératrices passées à `sum/min/max/any/all/sorted/list/set/tuple/join`, lambdas (comme valeurs typées),
`map/filter/reduce`, `[*a, *b]`, `{**a, **b}`, `a | b` (dict et set).

**Classes** : `__init__`, champs inférés, méthodes, `__str__/__repr__`, **héritage simple** (`super()`, méthodes virtuelles, `isinstance` avec
affinage de type, classes abstraites), `@dataclass` (`frozen`, `order`, `field(default_factory=…, compare=False)`, `__post_init__`), `NamedTuple`,
`@property` (+ setter), `@staticmethod`, `@classmethod`, variables de classe, **méthodes spéciales** `__len__ __bool__ __eq__ __lt__ __le__ __gt__ __ge__
__add__ __sub__ __mul__ __truediv__ __floordiv__ __mod__ __neg__ __getitem__ __setitem__ __contains__ __call__`, `Enum` (membres, `.name/.value`,
itération, recherche par valeur, clés de dict), classes comparables et hachables par identité.

**Exceptions** : `Exception` et toute la hiérarchie courante (`ValueError`, `KeyError`, `IndexError`, `ZeroDivisionError`, `TypeError`,
`AttributeError`, `RuntimeError`, `StopIteration`, `OverflowError`, `AssertionError`, `NotImplementedError`…), classes utilisateur dérivées,
exception non rattrapée → message sur stderr et code de sortie 1. Les erreurs de l'exécution (division par zéro, indice, clé, `int("x")`,
`math.sqrt(-1)`…) sont de vraies exceptions Python rattrapables.

**Bibliothèque** : `math` (fonctions, constantes, `comb perm prod isclose`, erreurs de domaine), `string`, `sys` (`exit`, `stdin.read/readline`,
`stdout.write`), `collections` (`deque`, `defaultdict`, `Counter`, `OrderedDict`), `heapq`, `bisect`, `itertools` (`product permutations combinations
accumulate chain islice pairwise repeat`), `functools` (`reduce`, `lru_cache`, `cache`), `random` (`seed random randint randrange uniform gauss choice
choices sample shuffle`, `random.Random(seed)`), `abc`, `enum`, `dataclasses`, `typing`. Méthodes de `str`, `list`, `dict`, `set`, `deque`, `int`.
`str.rsplit(sep, maxsplit)` et `rsplit(None, maxsplit)` sont pris en charge (blancs ASCII).

## Limites connues

Ce qui est refusé l'est explicitement (erreur avec numéro de ligne).

| Limite | Pourquoi / contournement |
|---|---|
| **Fonctions et paramètres annotés** (types explicites partout, sauf variables locales qui sont inférées) | le typage statique est la base de la conversion |
| `int` = **64 bits** : un dépassement lève `OverflowError` (jamais de résultat faux silencieux) | Python a des entiers non bornés. `factorial(25)` ou `2**100` ne passent pas |
| `str` : **ASCII** (octets) | `len` et l'indexation comptent des octets |
| `x: float = 3` : l'`int` est converti en float **avec un avertissement** (`--strict` pour refuser) | Python garderait un `int` (`print(x)` affiche `3`) |
| Une variable ne change pas de type (`a = 1` puis `a = "x"` refusé) | typage statique |
| Les `set` de `str`/tuples ne peuvent pas être parcourus ni affichés (`sorted(s)`, `len`, `in` oui) | leur ordre dépend du hachage aléatoire des chaînes en Python |
| Générateurs : seulement au premier niveau (pas imbriqués) ; `send()` non supporté ; une génératrice *expression* isolée refusée | |
| `enumerate/zip/reversed/map/filter` hors d'une itération (`print(zip(a, b))`) refusés | ce sont des itérateurs en Python |
| `with`, `yield` comme valeur, `async`, décorateurs utilisateur, métaclasses, héritage multiple, `__iter__/__next__`, `__hash__` | non encore pris en charge |
| `re`, `json`, `datetime`, `os`, fichiers (`open`), `time`, `decimal`, `fractions`, `complex`, `bytes` | non pris en charge |
| `Any`, `Union[A, B]` (seulement `Optional`), `getattr/setattr`, `type()`, `id()`, `hash()` | typage dynamique |
| `random.seed()` sans argument / sur `str` ; `random.getrandbits(k)` pour k > 63 | non reproductible / non supporté |
| Sorties flottantes : formatage identique à Python, mais les fonctions transcendantes dépendent de la libm (C++) / `StrictMath` (JVM) : dernier chiffre possible | |

from dataclasses import dataclass


@dataclass(frozen=True)
class Type:
    kind: str
    args: tuple = ()

    def __str__(self):
        return self.kind if not self.args else f"{self.kind}[{', '.join(map(str, self.args))}]"


INT, FLOAT, BOOL, STR, NONE = (Type(k) for k in ("int", "float", "bool", "str", "none"))


def list_of(t):
    return Type("list", (t,))


def dict_of(k, v):
    return Type("dict", (k, v))


def set_of(t):
    return Type("set", (t,))


def deque_of(t):
    return Type("deque", (t,))


def vtuple_of(t):
    """tuple de longueur variable homogène (tuple[int, ...], lignes de zip(*m)) : même représentation qu'une liste, mais immuable."""
    return Type("vtuple", (t,))


def func_of(params, ret):
    """Callable[[P1, P2], R] : args = (R, P1, P2)."""
    return Type("func", (ret,) + tuple(params))


def gen_of(t):
    """Générateur / itérateur Iterator[T] (à passage unique, évalué paresseusement)."""
    return Type("gen", (t,))


def tuple_of(*ts):
    return Type("tuple", tuple(ts))


def pending(token):
    """Type EN ATTENTE d'un littéral vide ([] ou {}) dont l'usage ultérieur révélera le type (inférence en deux passes)."""
    return Type("pending", (token,))


def has_pending(t):
    return t.kind == "pending" or any(isinstance(a, Type) and has_pending(a) for a in t.args)


def optional_of(t):
    """Optional[T] : T ou None. Une valeur déjà optionnelle ne s'emboîte pas (Optional[Optional[T]] = Optional[T])."""
    return t if t.kind == "optional" else Type("optional", (t,))


def is_optional(t):
    return t.kind == "optional"


def class_of(name):
    """Instance d'une classe utilisateur. Type RÉFÉRENCE (comme en Python) : shared_ptr en C++, référence en Kotlin."""
    return Type("class", (name,))


ORDERABLE_CLASSES = set()  # classes comparables avec < (définissent __lt__, ou @dataclass(order=True))
HASHABLE_CLASSES = set()  # classes dont les instances sont des singletons comparables par identité (membres d'Enum)


def is_hashable(t):
    """Types utilisables comme clés de dict."""
    return t in (INT, STR, BOOL) or (t.kind == "vtuple" and is_hashable(t.args[0])) or (t.kind == "class" and t.args[0] in HASHABLE_CLASSES) or (t.kind == "tuple" and all(is_hashable(a) for a in t.args))


def is_container(t):
    """Conteneurs MUTABLES (références partagées en Python). Les tuples sont immuables : copie et alias équivalents."""
    return t.kind in ("list", "dict", "set", "deque")


def is_value_type(t):
    """Tous les types sont désormais sûrs à copier : list/dict/objets sont des poignées partagées dans les deux cibles
    (copier la poignée = alias, comme en Python), les tuples sont immuables, les scalaires sont des valeurs."""
    return True


def is_orderable(t):
    """Types comparables avec < <= > >= (tuples : lexicographique, comme Python)."""
    return t in (INT, FLOAT, STR) or (t.kind == "class" and t.args[0] in ORDERABLE_CLASSES) or (t.kind == "vtuple" and is_orderable(t.args[0])) or (t.kind == "tuple" and all(a in (INT, FLOAT, STR, BOOL) or is_orderable(a) or (a.kind == "list" and is_orderable(a.args[0])) for a in t.args))


def is_numeric(t):
    return t in (INT, FLOAT)

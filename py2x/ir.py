"""Représentation intermédiaire : neutre, entièrement typée, sans sucre syntaxique Python.

Le frontend a déjà : inséré les conversions int->float (Cast), décomposé les comparaisons chaînées,
transformé `x += 1` en affectation, hoisté les variables déclarées dans des blocs imbriqués.
Un émetteur n'a donc qu'à traduire nœud par nœud.
"""
from dataclasses import dataclass, field
from .types import Type, BOOL


# ---------- expressions ----------
@dataclass
class Const:
    value: object
    type: Type


@dataclass
class Var:
    name: str
    type: Type


@dataclass
class BinOp:
    op: str  # + - * / // % ** & | ^ << >>
    left: object
    right: object
    type: Type


@dataclass
class Cmp:
    op: str  # == != < <= > >= in notin
    left: object
    right: object
    type: Type = BOOL


@dataclass
class BoolOp:
    op: str  # and | or
    values: list
    type: Type = BOOL


@dataclass
class Unary:
    op: str  # not - + ~
    operand: object
    type: Type


@dataclass
class Ternary:
    cond: object
    a: object
    b: object
    type: Type


@dataclass
class Cast:
    operand: object
    type: Type  # int<->float, bool->int, bool->float


@dataclass
class Call:
    name: str
    args: list
    type: Type
    kind: str  # "user" | "builtin"


@dataclass
class MethodCall:
    obj: object
    name: str  # append | sort | reverse | get | keys | values | items
    args: list
    type: Type


@dataclass
class Index:
    base: object
    index: object
    type: Type


@dataclass
class ListLit:
    elems: list
    type: Type


@dataclass
class DictLit:
    keys: list
    values: list
    type: Type


@dataclass
class DictNew:
    """dict à comportement propre : mode 1 defaultdict, 2 Counter, 3 OrderedDict (le dict garde son type dict[K, V])."""
    mode: int
    factory: str
    type: Type


@dataclass
class TupleLit:
    elems: list
    type: Type


@dataclass
class TupleGet:
    base: object
    index: int  # constante, déjà normalisée (indices négatifs résolus)
    type: Type


@dataclass
class Attr:
    obj: object  # expression de type class (ou Var "self")
    name: str
    type: Type


@dataclass
class New:
    cls: str
    args: list  # arguments déjà liés dans l'ordre des paramètres, valeurs par défaut incluses
    type: Type


@dataclass
class NoneOf:
    """None typé comme Optional[T]."""
    type: Type


@dataclass
class Wrap:
    """T -> Optional[T]."""
    operand: object
    type: Type


@dataclass
class Unwrap:
    """Optional[T] -> T avec vérification à l'exécution : lève l'erreur de Python si la valeur est None."""
    operand: object
    type: Type


@dataclass
class IsNone:
    operand: object
    negate: bool  # True : `is not None`
    type: Type = BOOL


@dataclass
class Lambda:
    """Fonction à un paramètre passée en key= (lambda x: ..., len, str.lower, fonction utilisateur)."""
    param: str
    ptype: Type
    body: object


@dataclass
class KeyOp:
    """sorted/sort/min/max avec une fonction clé. kind : sorted | sort | min | max."""
    kind: str
    args: list  # [liste]
    lam: object
    rev: object  # expression bool
    type: Type


@dataclass
class Slice:
    """base[lo:hi:step] sur une liste ou une chaîne ; chaque borne peut être None (omise)."""
    base: object
    lo: object
    hi: object
    step: object
    type: Type


@dataclass
class SliceAssign:
    base: object
    lo: object
    hi: object
    step: object
    value: object


@dataclass
class Delete:
    kind: str  # item | slice | key
    base: object
    args: list


@dataclass
class LibConst:
    """Constante de la bibliothèque standard (math.pi, math.inf, sys.maxsize...)."""
    name: str
    type: Type


@dataclass
class Comp:
    """Compréhension de liste/dict : un bloc d'instructions (boucles, if) qui remplit la variable locale `result`."""
    result: str
    type: Type
    body: list


@dataclass
class UserMethodCall:
    obj: object
    cls: str
    name: str
    args: list
    type: Type


# ---------- instructions ----------
@dataclass
class VarDecl:
    name: str
    type: Type
    init: object = None  # None -> valeur par défaut du type


@dataclass
class Assign:
    target: object  # Var | Index
    value: object


@dataclass
class If:
    cond: object
    body: list
    orelse: list


@dataclass
class While:
    cond: object
    body: list


@dataclass
class ForRange:
    var: str
    start: object
    stop: object
    step: int  # constante non nulle
    body: list


@dataclass
class ForEach:
    var: str
    iterable: object  # list ou dict (on itère sur les clés)
    elem_type: Type
    body: list


@dataclass
class Return:
    value: object = None


@dataclass
class Break:
    pass


@dataclass
class Continue:
    pass


@dataclass
class ExprStmt:
    expr: object


@dataclass
class Print:
    args: list
    sep: object = None  # expression str ou None (défaut " ")
    end: object = None  # expression str ou None (défaut "\n")
    err: bool = False  # sys.stderr


@dataclass
class Func:
    name: str
    params: list  # [(nom, Type)]
    ret: Type
    body: list
    hoisted: list = field(default_factory=list)  # [(nom, Type)] déclarés en tête de fonction
    mutated: set = field(default_factory=set)  # paramètres conteneurs modifiés dans la fonction
    reassigned: set = field(default_factory=set)  # paramètres réaffectés (x = ...)
    owner: str = None  # nom de la classe pour une méthode (self n'est pas dans params)
    is_gen: bool = False  # fonction génératrice (contient yield)


@dataclass
class ClassDef:
    name: str
    fields: list  # [(nom, Type, défaut ou None)] dans l'ordre de déclaration
    is_dataclass: bool
    frozen: bool
    init: object  # Func __init__ (classe ordinaire) ou None (dataclass : constructeur généré)
    methods: list  # [Func] hors __init__
    has_str: bool = False  # définit __str__ (ou en hérite)
    has_repr: bool = False  # définit __repr__ (ou en hérite)
    base: str = None  # classe parente (utilisateur ou exception intégrée)
    hier: bool = False  # participe à une hiérarchie (a un parent ou des enfants) : méthodes virtuelles, init séparé
    is_exc: bool = False  # dérive de Exception
    overrides: set = field(default_factory=set)  # méthodes qui redéfinissent celles d'un ancêtre
    init_owner: str = None  # classe dont le __init__ sert de constructeur (la sienne ou celle d'un ancêtre), None si aucun
    init_params: list = field(default_factory=list)  # paramètres du constructeur effectif
    has_eq: bool = False  # définit __eq__ (ou en hérite)
    has_lt: bool = False  # définit __lt__ (ou en hérite)
    lt_root: bool = False  # première classe de la hiérarchie à définir __lt__ (porte l'interface Comparable en Kotlin)
    has_post_init: bool = False  # dataclass avec __post_init__
    nocompare: set = field(default_factory=set)  # champs de dataclass exclus de la comparaison (field(compare=False))


@dataclass
class LambdaVal:
    """Lambda utilisée comme valeur (type func) : capture par valeur."""
    params: list  # [(nom, Type)]
    body: object
    type: Type


@dataclass
class FuncRef:
    """Nom de fonction utilisé comme valeur."""
    name: str
    kind: str  # "user" | "local"
    type: Type


@dataclass
class CallVal:
    """Appel d'une valeur de type func."""
    fn: object
    args: list
    type: Type


@dataclass
class Yield:
    value: object


@dataclass
class LocalFunc:
    """Fonction imbriquée : capture les variables de la fonction englobante par référence (lambda [&] en C++, fonction locale en Kotlin) ;
    si elle sert de VALEUR (retournée, passée), elle survit à la fonction englobante : capture par copie."""
    func: object
    escapes: bool = False
    recursive: bool = False


@dataclass
class SuperCall:
    """super().méthode(args) ; owner = classe ancêtre qui définit la méthode (None : parent intégré, exception)."""
    owner: str
    name: str
    args: list
    type: Type


@dataclass
class IsInstance:
    operand: object
    classes: list
    type: Type = BOOL


@dataclass
class Downcast:
    operand: object
    type: Type


@dataclass
class Handler:
    classes: list  # noms de classes, None pour `except:`
    var: str  # nom lié par `as`, ou None
    vtype: Type
    body: list


@dataclass
class Try:
    body: list
    handlers: list
    orelse: list
    final: list


@dataclass
class Raise:
    value: object  # expression, ou None (re-lève l'exception en cours de traitement)


@dataclass
class Module:
    funcs: list
    entry: object = None  # Func "__entry__" : code de niveau module et bloc `if __name__ == "__main__"`, ou None
    classes: list = field(default_factory=list)
    globals: list = field(default_factory=list)  # [(nom, Type)] variables de module, visibles de toutes les fonctions
    has_main: bool = True  # le fichier a un bloc `if __name__ == "__main__"` (programme) ; sinon c'est une bibliothèque

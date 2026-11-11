"""Frontend : source Python (sous-ensemble typé) -> IR typée.

Sous-ensemble supporté : fonctions de premier niveau annotées ; int/float/bool/str/list/dict ;
if/elif/else, while, for sur range() ou sur list/dict ; break/continue/return ; print() ;
arithmétique avec la sémantique de Python (// et % arrondis vers le bas, indices négatifs) ;
f-strings simples ; échange `a, b = b, a`. Le reste lève Unsupported avec le numéro de ligne.
"""
import ast
import copy
import re

from . import ir
from .coll_fe import COLL_MODULES, COLL_NAMES, CollectionsMixin
from .builtins_fe import BuiltinsMixin, GlobalDefault, WS
from .classes_fe import ClassesMixin
from .enum_fe import EnumMixin
from .std_fe import StdMixin
from .random_prelude import PRELUDE as RANDOM_PRELUDE
from . import types as _types
from .excs import BUILTIN_EXC
from .errors import Unsupported
from .lib import CONSTS, LIB, LOG, MODULES, IGNORED_MODULES, STRING_CONSTS
from .types import (BOOL, FLOAT, INT, NONE, STR, Type, class_of, dict_of, has_pending, is_container, is_hashable,
                    is_numeric, is_optional, is_orderable, is_value_type, list_of, optional_of, pending, tuple_of, set_of, deque_of, vtuple_of, func_of, gen_of)

BINOPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%", ast.Pow: "**",
          ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^", ast.LShift: "<<", ast.RShift: ">>"}
CMPOPS = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
          ast.In: "in", ast.NotIn: "notin", ast.Is: "is", ast.IsNot: "isnot"}
INT64 = 2 ** 63


def parse_type(node, classes=None):
    """Annotation -> Type. `classes` : dict nom -> Type des classes et alias du module (une annotation peut aussi être une chaîne "Point")."""
    classes = classes or {}
    if isinstance(node, ast.Constant) and node.value is None:
        return NONE
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            node = ast.parse(node.value, mode="eval").body
        except SyntaxError:
            raise Unsupported(f"annotation en chaîne invalide : {node.value!r}", node)
    if isinstance(node, ast.Name):
        simple = {"int": INT, "float": FLOAT, "bool": BOOL, "str": STR}
        if node.id in simple:
            return simple[node.id]
        if node.id in classes:
            return classes[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):  # T | None
        l, r = parse_type(node.left, classes), parse_type(node.right, classes)
        if r == NONE and l != NONE:
            return optional_of(l)
        if l == NONE and r != NONE:
            return optional_of(r)
        raise Unsupported(f"union de types non supportée : {ast.unparse(node)} (seulement T | None)", node)
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        n = node.value.id
        if n == "Optional":
            return optional_of(parse_type(node.slice, classes))
        if n == "Union":
            elts = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            ts = [parse_type(e, classes) for e in elts]
            real = [t for t in ts if t != NONE]
            if len(ts) == 2 and len(real) == 1:
                return optional_of(real[0])
            raise Unsupported(f"Union non supporté : {ast.unparse(node)} (seulement Union[T, None])", node)
        if n in ("ClassVar", "Final"):
            return parse_type(node.slice, classes)
        if n in ("list", "List"):
            return list_of(parse_type(node.slice, classes))
        if n in ("Iterator", "Generator"):
            elts = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            return gen_of(parse_type(elts[0], classes))
        if n in ("Iterable", "Sequence", "MutableSequence"):
            return list_of(parse_type(node.slice, classes))
        if n == "Callable":
            elts = node.slice.elts if isinstance(node.slice, ast.Tuple) else []
            if len(elts) != 2 or not isinstance(elts[0], ast.List):
                raise Unsupported("Callable[[P1, P2], R] attendu (Callable[..., R] non supporté)", node)
            return func_of([parse_type(a, classes) for a in elts[0].elts], parse_type(elts[1], classes))
        if n in ("set", "Set", "deque", "Deque", "Counter"):
            et = parse_type(node.slice, classes)
            if not is_hashable(et):
                raise Unsupported(f"élément de {n} non supporté : {et} (int, str, bool et tuples de ces types)", node)
            return {"set": set_of, "Set": set_of, "deque": deque_of, "Deque": deque_of}[n](et) if n != "Counter" else dict_of(et, INT)
        if n in ("defaultdict", "DefaultDict", "OrderedDict") and isinstance(node.slice, ast.Tuple) and len(node.slice.elts) == 2:
            k, v = (parse_type(e, classes) for e in node.slice.elts)
            if not is_hashable(k):
                raise Unsupported(f"clé de dict non supportée : {k} (int, str, bool et tuples de ces types)", node)
            return dict_of(k, v)
        if n in ("dict", "Dict") and isinstance(node.slice, ast.Tuple) and len(node.slice.elts) == 2:
            k, v = (parse_type(e, classes) for e in node.slice.elts)
            if not is_hashable(k):
                raise Unsupported(f"clé de dict non supportée : {k} (int, str, bool et tuples de ces types)", node)
            return dict_of(k, v)
        if n in ("tuple", "Tuple"):
            elts = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            if len(elts) == 2 and isinstance(elts[1], ast.Constant) and elts[1].value is Ellipsis:
                et = parse_type(elts[0], classes)
                return vtuple_of(et)
            if any(isinstance(e, ast.Constant) and e.value is Ellipsis for e in elts):
                raise Unsupported("tuple de longueur variable : seule la forme tuple[T, ...] est supportée", node)
            ts = [parse_type(e, classes) for e in elts]
            for t in ts:
                if not is_value_type(t):
                    raise Unsupported(f"élément de tuple non supporté : {t} (seulement int, float, bool, str, objets et tuples : "
                                      "en Python un tuple contenant une liste partage sa référence)", node)
            return tuple_of(*ts)
    raise Unsupported(f"type non supporté : {ast.unparse(node)}", node)


def root_var(e):
    while isinstance(e, ir.Index):
        e = e.base
    return e if isinstance(e, ir.Var) else None


class ClassInfo:
    """Classe utilisateur pendant la conversion : champs, signatures des méthodes."""

    def __init__(self, name, is_dataclass, frozen):
        self.name, self.is_dataclass, self.frozen = name, is_dataclass, frozen
        self.fields = {}  # nom -> (Type, défaut ir ou None), dans l'ordre
        self.methods = {}  # nom -> (params, ret, défauts) ; params sans self
        self.nodes = {}  # nom -> ast.FunctionDef
        self.base = None  # nom de la classe parente (utilisateur ou exception intégrée)
        self.builtin = False  # exception intégrée (ValueError...)
        self.is_exc = False  # dérive de Exception
        self.is_namedtuple = False
        self.nocompare = set()
        self.classvars = {}  # variable de classe -> nom de la globale de module qui la porte
        self.enum_members = []  # [(membre, globale)] si la classe est un Enum
        self.module_stmts = []  # instructions de module synthétisées (variables de classe, membres d'Enum)
        self.props = {}  # nom de propriété @property -> type
        self.setters = set()  # propriétés avec @x.setter (méthode set_prop_<x>)
        self.statics = {}  # nom -> (fonction de module, est_classmethod, classe propriétaire)


class Frontend(EnumMixin, StdMixin):
    def __init__(self, hints=None, dry=False, strict=False):
        self.sigs = {}  # fonction -> (params, ret)
        self.fdefaults = {}  # fonction -> {param: Const}
        self.classes = {}  # nom -> ClassInfo
        for n, parent in BUILTIN_EXC.items():
            ci = ClassInfo(n, False, False)
            ci.base, ci.builtin, ci.is_exc = parent, True, True
            self.classes[n] = ci
        self.pre_globals = {}
        _types.HASHABLE_CLASSES.clear()
        self.warnings = []  # avertissements non bloquants (conversions implicites int -> float...)
        self.strict = strict
        self.extra_defs = []  # fonctions de module issues des @staticmethod / @classmethod
        self.class_names = frozenset()
        self.type_names = {}  # classes + alias de types (Grid = list[list[int]])
        self.globals = {}  # variables de module : nom -> Type
        self.modules = {}  # alias -> module importé (math, string...)
        self.from_imports = {}  # nom -> "module.membre" (from math import sqrt)
        # inférence des littéraux vides : token (position du [] / {}) -> type d'élément / de clé / de valeur
        self.hints = dict(hints or {})
        self.global_keys = {}
        self.dry = dry  # passe « à blanc » : collecte des indices, les erreurs sont tolérées
        self.changed = False

    def warn(self, msg, node=None):
        line = getattr(node, "lineno", None)
        w = f"ligne {line} : {msg}" if line else msg
        if w not in self.warnings:
            self.warnings.append(w)

    # ---------- hiérarchie de classes ----------
    def chain(self, cname):
        out = []
        while cname is not None:
            info = self.classes[cname]
            out.append(info)
            cname = info.base
        return out

    def lookup_field(self, cname, attr):
        for info in self.chain(cname):
            if attr in info.fields:
                return info, info.fields[attr]
        return None

    def lookup_method(self, cname, m):
        for info in self.chain(cname):
            if m in info.methods:
                return info, info.methods[m]
        return None

    def lookup_classvar(self, cname, attr):
        for info in self.chain(cname):
            if attr in info.classvars:
                return info.classvars[attr]
        return None

    def lookup_prop(self, cname, attr):
        for info in self.chain(cname):
            if attr in info.props:
                return info.props[attr]
        return None

    def has_setter(self, cname, attr):
        return any(attr in info.setters for info in self.chain(cname))

    def effective_init(self, cname):
        return self.lookup_method(cname, "__init__")

    def is_subclass(self, a, b):
        return any(i.name == b for i in self.chain(a))

    def lub_class(self, names):
        """Plus proche ancêtre commun d'une liste de classes (ou None)."""
        for info in self.chain(names[0]):
            if all(self.is_subclass(n, info.name) for n in names):
                return info.name
        return None

    def sub_ok(self, a, b):
        return a.kind == "class" and b.kind == "class" and self.is_subclass(a.args[0], b.args[0])

    # ---------- inférence des littéraux vides ----------
    def resolve(self, t):
        """Remplace les types en attente par leur indice quand il est connu."""
        if t.kind == "pending":
            h = self.hints.get(t.args[0])
            return self.resolve(h) if h is not None and h != t else t
        if t.kind in ("list", "dict", "tuple", "set", "deque", "vtuple", "func") and has_pending(t):
            return Type(t.kind, tuple(self.resolve(a) for a in t.args))
        return t

    def set_hint(self, token, t):
        t = self.resolve(t)
        if t.kind == "pending" and t.args[0] == token:
            return
        cur = self.hints.get(token)
        if cur is None or (has_pending(cur) and not has_pending(t)):
            self.hints[token] = t
            self.changed = True

    def unify(self, a, b):
        """a et b désignent-ils le même type ? Si l'un contient un type en attente, enregistre l'indice correspondant."""
        a, b = self.resolve(a), self.resolve(b)
        if a == b:
            return True
        if a.kind == "pending":
            self.set_hint(a.args[0], b)
            return True
        if b.kind == "pending":
            self.set_hint(b.args[0], a)
            return True
        if a.kind == b.kind and a.kind in ("list", "dict", "tuple", "set", "deque", "vtuple", "func") and len(a.args) == len(b.args):
            return all([self.unify(x, y) for x, y in zip(a.args, b.args)])
        if a.kind == "optional" and b.kind == "optional":
            return self.unify(a.args[0], b.args[0])
        return False

    def widened(self, key, t):
        """Une variable/un champ dont la passe à blanc a vu une affectation de None devient Optional[T]."""
        return optional_of(t) if self.hints.get(("widen", key)) and t != NONE else t

    # ---------- module ----------
    def convert(self, source):
        tree = ast.parse(source)
        if any((isinstance(n, ast.Import) and any(a.name == "random" for a in n.names)) or (isinstance(n, ast.ImportFrom) and n.module == "random")
               for n in tree.body):
            tree.body = ast.parse(RANDOM_PRELUDE).body + tree.body  # générateur Mersenne Twister de CPython, en Python typé
        tree.body = [m for node in tree.body for m in (self.memoize(node) if isinstance(node, ast.FunctionDef) and self.memo_decorator(node) else [node])]
        self.class_names = frozenset(n.name for n in tree.body if isinstance(n, ast.ClassDef))
        for n in tree.body:  # une classe sans __eq__ ni @dataclass est hachable par identité (clé de dict, élément de set)
            if isinstance(n, ast.ClassDef) and not n.decorator_list and not any(isinstance(b, ast.FunctionDef) and b.name == "__eq__" for b in n.body) \
                    and not any(isinstance(b, ast.Name) and b.id in ("Enum", "NamedTuple") for b in n.bases):
                _types.HASHABLE_CLASSES.add(n.name)
        self.type_names = {n: class_of(n) for n in list(self.class_names) + list(BUILTIN_EXC)}
        # alias de types : Grid = list[list[int]]  (doivent être connus avant les signatures)
        aliases = set()
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                    and self.is_type_expr(node.value):
                self.type_names[node.targets[0].id] = parse_type(node.value, self.type_names)
                aliases.add(id(node))
        defs, class_nodes, module_stmts, guard_seen = [], [], [], False
        for node in tree.body:
            if id(node) in aliases:
                continue
            if isinstance(node, ast.FunctionDef):
                self.register(node)
                defs.append(node)
            elif isinstance(node, ast.ClassDef):
                enum_info = None
                if self.is_enum_class(node):
                    node, stmts, fd, members, vt = self.expand_enum(node)
                    enum_info = (members, stmts, fd)
                    _types.HASHABLE_CLASSES.add(node.name)
                self.register_class(node)
                info = self.classes[node.name]
                if enum_info is not None:
                    info.enum_members = enum_info[0]
                    info.classvars.update(dict(enum_info[0]))
                    self.register(enum_info[2])
                    self.extra_defs.append(enum_info[2])
                    module_stmts.extend(enum_info[1])
                module_stmts.extend(info.module_stmts)
                class_nodes.append(node)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                self.register_import(node)
            elif isinstance(node, ast.If) and self.is_main_guard(node):
                if guard_seen:
                    raise Unsupported("deux blocs `if __name__ == \"__main__\"`", node)
                guard_seen = True
                module_stmts.extend(node.body)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                continue  # docstring de module
            else:
                module_stmts.append(node)  # constante globale, appel, boucle... : exécuté dans l'ordre au démarrage
        defs.extend(self.extra_defs)
        _types.ORDERABLE_CLASSES.clear()
        for cname in self.classes:
            if self.lookup_method(cname, "__lt__") is not None:
                _types.ORDERABLE_CLASSES.add(cname)
        # 0) types des variables de module : les __init__ des classes en ont besoin (self.state = IDLE) avant le code de module
        self.pre_globals = {}
        if module_stmts:
            saved = (dict(self.globals), dict(self.global_keys), self.changed, self.dry)
            pre = FuncConv(self, "__entry__", [], NONE, module=True)
            self.dry = True
            try:
                for st in module_stmts:
                    try:
                        pre.run([st])
                    except Unsupported:
                        pass
            finally:
                self.pre_globals = dict(self.globals)
                self.globals.clear()
                self.globals.update(saved[0])
                self.global_keys.clear()
                self.global_keys.update(saved[1])
                self.changed, self.dry = saved[2], saved[3]
        convs = []
        # 1) les __init__ d'abord : ils révèlent les champs des classes ordinaires (self.x = ...)
        method_funcs = {}  # (classe, méthode) -> Func
        for cn in class_nodes:
            info = self.classes[cn.name]
            if "__init__" in info.nodes:
                self.convert_method(info, "__init__", convs, method_funcs)
        # 2) le code de niveau module (déclare les variables globales visibles des fonctions)
        entry = None
        if module_stmts:
            c = FuncConv(self, "__entry__", [], NONE, module=True)
            convs.append((c, c.run(module_stmts)))
            entry = convs[-1][1]
        # 3) les autres méthodes, puis les fonctions
        for cn in class_nodes:
            info = self.classes[cn.name]
            for m in info.nodes:
                if m != "__init__":
                    self.convert_method(info, m, convs, method_funcs)
        for node in defs:
            params, ret = self.sigs[node.name]
            c = FuncConv(self, node.name, params, ret)
            if self.dry:
                try:
                    convs.append((c, c.run(node.body)))
                except Unsupported:
                    pass
            else:
                convs.append((c, c.run(node.body)))
        self.propagate_mutations(convs)
        funcs = [f for c, f in convs if f is not entry and f.owner is None]
        classes = []
        for cn in class_nodes:
            info = self.classes[cn.name]
            eff = self.effective_init(info.name)
            hier = info.base is not None or any(c.base == info.name for c in self.classes.values())
            classes.append(ir.ClassDef(
                info.name, [(n, t, d) for n, (t, d) in info.fields.items()], info.is_dataclass, info.frozen,
                method_funcs.get((info.name, "__init__")),
                [method_funcs[(info.name, m)] for m in info.nodes if m != "__init__"],
                self.lookup_method(info.name, "__str__") is not None, self.lookup_method(info.name, "__repr__") is not None,
                info.base, hier, info.is_exc,
                {m for m in info.nodes if m != "__init__" and info.base and self.lookup_method(info.base, m)},
                eff[0].name if eff else None, list(eff[1][0]) if eff else [],
                self.lookup_method(info.name, "__eq__") is not None, self.lookup_method(info.name, "__lt__") is not None,
                "__lt__" in info.methods and (info.base is None or self.lookup_method(info.base, "__lt__") is None),
                "__post_init__" in info.methods, set(info.nocompare)))
        globals_ = [(n, self.resolve(t)) for n, t in self.globals.items()]
        return ir.Module(funcs, entry, classes, globals_, guard_seen)

    def is_type_expr(self, node):
        """`Grid = list[list[int]]` ou `Pair = tuple[int, int]` : une affectation de module qui définit un alias de type."""
        if isinstance(node, ast.Name):
            return node.id in ("int", "float", "bool", "str") or node.id in self.type_names
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) \
                and node.value.id in ("list", "List", "dict", "Dict", "tuple", "Tuple", "set", "Set", "deque", "Deque", "Counter", "Callable",
                                      "defaultdict", "DefaultDict", "OrderedDict"):
            try:
                parse_type(node, self.type_names)
                return True
            except Unsupported:
                return False
        return False

    def register_import(self, node):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name in MODULES or a.name in COLL_MODULES:
                    self.modules[a.asname or a.name] = a.name
                elif a.name not in IGNORED_MODULES:
                    raise Unsupported(f"module {a.name} non supporté (supportés : {', '.join(sorted(MODULES))})", node)
            return
        if node.module in IGNORED_MODULES:
            return
        if node.module in COLL_MODULES:
            for a in node.names:
                if a.name not in COLL_NAMES[node.module]:
                    raise Unsupported(f"{node.module}.{a.name} non supporté", node)
                self.from_imports[a.asname or a.name] = f"{node.module}.{a.name}"
            return
        if node.module not in MODULES:
            raise Unsupported(f"module {node.module} non supporté (supportés : {', '.join(sorted(MODULES | COLL_MODULES))})", node)
        for a in node.names:
            q = f"{node.module}.{a.name}"
            if q not in LIB and q not in CONSTS and q not in STRING_CONSTS and q not in ("math.log", "math.prod"):
                raise Unsupported(f"{q} non supporté", node)
            self.from_imports[a.asname or a.name] = q

    def convert_method(self, info, name, convs, method_funcs):
        params, ret, _ = info.methods[name]
        c = FuncConv(self, name, params, ret, cls=info.name)
        try:
            f = c.run(info.nodes[name].body)
        except Unsupported:
            if not self.dry:
                raise
            f = ir.Func(name, params, ret, [], owner=info.name)  # passe à blanc : on garde un squelette
        convs.append((c, f))
        method_funcs[(info.name, name)] = f

    @staticmethod
    def is_main_guard(node):
        t = node.test
        return (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name) and t.left.id == "__name__"
                and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq)
                and isinstance(t.comparators[0], ast.Constant) and t.comparators[0].value == "__main__")

    def params_and_defaults(self, node, skip=0):
        """Paramètres annotés (sans les `skip` premiers, ex. self) et valeurs par défaut CONSTANTES (int/float/bool/str)."""
        a = node.args
        if a.kwarg or a.posonlyargs:
            raise Unsupported("**kwargs et paramètres positional-only non supportés", node)
        params = []
        for arg in a.args[skip:] + a.kwonlyargs:  # keyword-only : acceptés comme paramètres ordinaires (superset)
            if arg.annotation is None:
                raise Unsupported(f"paramètre '{arg.arg}' sans annotation de type", node)
            params.append((arg.arg, parse_type(arg.annotation, self.type_names)))
        defaults = {}
        n_pos = len(a.args) - skip
        for j, (arg, d) in enumerate(zip(a.kwonlyargs, a.kw_defaults)):
            if d is not None:
                defaults[arg.arg] = self.const_default(d, params[n_pos + j][1], node)
        if a.vararg:  # *nums: int -> dernier paramètre, de type tuple[int, ...]
            if a.vararg.annotation is None:
                raise Unsupported(f"*{a.vararg.arg} sans annotation de type", node)
            if a.kwonlyargs:
                raise Unsupported("*args combiné à des paramètres keyword-only non supporté", node)
            params.append((a.vararg.arg, vtuple_of(parse_type(a.vararg.annotation, self.type_names))))
            defaults["__vararg__"] = True
        offset = len(a.args) - len(a.defaults)  # les défauts s'alignent sur la fin de la liste (self inclus)
        for i, d in enumerate(a.defaults):
            idx = offset + i - skip
            if idx < 0:
                raise Unsupported("valeur par défaut sur self", node)
            pname, pt = params[idx]
            defaults[pname] = self.const_default(d, pt, node)
        return params, defaults

    def const_default(self, d, t, node):
        if isinstance(d, ast.Constant) and d.value is None:
            if t.kind != "optional":
                raise Unsupported("valeur par défaut None : le type du paramètre/champ doit être Optional[...]", node)
            return ir.NoneOf(t)
        if isinstance(d, ast.Attribute) and isinstance(d.value, ast.Name) and d.value.id in self.classes \
                and d.attr in self.classes[d.value.id].classvars:
            return GlobalDefault(self.classes[d.value.id].classvars[d.attr])  # membre d'Enum / variable de classe : lu à chaque appel
        if isinstance(d, ast.Name) and d.id not in ("True", "False", "None"):
            return GlobalDefault(d.id)  # constante de module lue à chaque appel (Python la lit à la définition : même valeur si non réaffectée)
        lit = self.literal(d)
        if lit is None:
            raise Unsupported("valeur par défaut : seules les constantes (int, float, bool, str) sont supportées "
                              "(Python évalue les défauts une seule fois : un défaut mutable est un piège)", node)
        value, lt = lit
        if lt != t:
            hint = " (écrivez 0.0 plutôt que 0 : Python ne convertit pas)" if t == FLOAT and lt == INT else ""
            raise Unsupported(f"valeur par défaut de type {lt} pour un paramètre/champ {t}{hint}", node)
        return ir.Const(value, t)

    @staticmethod
    def literal(d):
        sign = 1
        if isinstance(d, ast.UnaryOp) and isinstance(d.op, ast.USub):
            sign, d = -1, d.operand
        if not isinstance(d, ast.Constant) or d.value is None or (sign == -1 and isinstance(d.value, (bool, str))):
            return None
        v = d.value
        if isinstance(v, bool):
            return v, BOOL
        if isinstance(v, int):
            return sign * v, INT
        if isinstance(v, float):
            return sign * v, FLOAT
        if isinstance(v, str):
            return v, STR
        return None

    @staticmethod
    def is_generator(node):
        stack = list(node.body)
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.Yield, ast.YieldFrom)):
                return True
            if isinstance(n, (ast.FunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            stack.extend(ast.iter_child_nodes(n))
        return False

    def ret_type(self, node):
        """Type de retour annoté ; une fonction génératrice (yield) rend un Iterator[T] / Generator[T, None, None] / Iterable[T]."""
        if self.is_generator(node):
            r = node.returns
            if isinstance(r, ast.Subscript) and isinstance(r.value, ast.Name) and r.value.id in ("Iterator", "Generator", "Iterable"):
                elt = r.slice.elts[0] if isinstance(r.slice, ast.Tuple) else r.slice
                return gen_of(parse_type(elt, self.type_names))
            raise Unsupported("fonction génératrice : annotez le retour Iterator[T] / Generator[T, None, None] / Iterable[T]", node)
        return parse_type(node.returns, self.type_names)

    def register(self, node):
        if node.decorator_list:
            raise Unsupported("décorateur de fonction non supporté", node)
        if node.returns is None:
            raise Unsupported(f"annotation de retour manquante pour {node.name}() (écrire -> None si rien)", node)
        params, defaults = self.params_and_defaults(node)
        if node.name in self.sigs or node.name in self.class_names:
            raise Unsupported(f"nom {node.name} défini deux fois", node)
        self.sigs[node.name] = (params, self.ret_type(node))
        self.fdefaults[node.name] = defaults

    # ---------- classes ----------
    @staticmethod
    def decorator_info(d):
        """@dataclass, @dataclass(frozen=True), @dataclasses.dataclass -> (nom, [keywords])."""
        kws = []
        if isinstance(d, ast.Call):
            kws, d = d.keywords, d.func
        if isinstance(d, ast.Attribute):
            return d.attr, kws
        if isinstance(d, ast.Name):
            return d.id, kws
        return "?", kws

    def register_class(self, node):
        base = None
        is_nt = False
        order = False
        if node.keywords or len(node.bases) > 1:
            raise Unsupported("héritage multiple / mots-clés de classe (metaclass...) non supportés", node)
        if node.bases:
            b = node.bases[0]
            bn = b.id if isinstance(b, ast.Name) else (b.attr if isinstance(b, ast.Attribute) else None)
            if bn in ("ABC", "object"):
                base = None
            elif bn == "NamedTuple":
                base = None
                is_nt = True
            elif bn in self.classes:
                base = bn
            else:
                raise Unsupported(f"classe parente non supportée : {ast.unparse(b)} (classes du fichier et exceptions intégrées)", node)
        if node.name in self.sigs or node.name in self.classes:
            raise Unsupported(f"nom {node.name} défini deux fois", node)
        is_dc = frozen = False
        for d in node.decorator_list:
            name, kws = self.decorator_info(d)
            if name != "dataclass":
                raise Unsupported(f"décorateur @{name} non supporté sur une classe", node)
            is_dc = True
            for k in kws:
                if k.arg in ("frozen", "order") and isinstance(k.value, ast.Constant) and isinstance(k.value.value, bool):
                    if k.arg == "frozen":
                        frozen = k.value.value
                    else:
                        order = k.value.value
                elif k.arg in ("eq", "repr", "init") and isinstance(k.value, ast.Constant) and k.value.value is True:
                    pass
                else:
                    raise Unsupported(f"option @dataclass({k.arg}=...) non supportée (supportées : frozen, order ; eq/repr/init=True)", node)
        if is_nt:
            is_dc, frozen, order = True, True, True
        if base is not None and (is_dc or self.classes[base].is_dataclass):
            raise Unsupported("@dataclass combiné à l'héritage non supporté", node)
        info = ClassInfo(node.name, is_dc, frozen)
        info.is_namedtuple = is_nt
        info.base = base
        info.is_exc = base is not None and self.classes[base].is_exc
        self.classes[node.name] = info
        seen_default = False
        for st in node.body:
            if isinstance(st, ast.Pass) or (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant)):
                continue
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                info.module_stmts.append(self.class_var_stmts(info, st))  # variable de classe -> globale de module
                continue
            if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name) and st.value is not None and not is_dc:
                info.module_stmts.append(self.class_var_stmts(info, st))
                continue
            if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name):
                t = parse_type(st.annotation, self.type_names)
                default = None
                if st.value is not None:
                    if isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Name) and st.value.func.id == "field":
                        for kw in st.value.keywords:
                            if kw.arg == "compare" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                                info.nocompare.add(st.target.id)
                    default = self.field_default(st.value, t, st)
                    seen_default = seen_default or default is not None
                elif is_dc and seen_default:
                    raise Unsupported(f"champ '{st.target.id}' sans valeur par défaut après un champ avec valeur par défaut", st)
                if st.target.id in info.fields:
                    raise Unsupported(f"champ '{st.target.id}' déclaré deux fois", st)
                info.fields[st.target.id] = (t, default)
            elif isinstance(st, ast.FunctionDef):
                self.register_method(info, st)
            else:
                raise Unsupported(f"instruction non supportée dans le corps d'une classe : {type(st).__name__}", st)
        if is_dc and "__init__" in info.methods:
            raise Unsupported("@dataclass avec __init__ explicite non supporté (le constructeur est généré)", node)
        if order:  # @dataclass(order=True) : __lt__ & co comparent les champs comme un tuple
            names = [n for n in info.fields if n not in info.nocompare]
            if not names:
                raise Unsupported("@dataclass(order=True) sans champ comparable", node)
            tup = lambda v: "(" + ", ".join(f"{v}.{n}" for n in names) + ("," if len(names) == 1 else "") + ")"  # noqa: E731
            for dn, op in (("__lt__", "<"), ("__le__", "<="), ("__gt__", ">"), ("__ge__", ">=")):
                fd = ast.parse(f'def {dn}(self, other: "{info.name}") -> bool:\n    return {tup("self")} {op} {tup("other")}\n').body[0]
                for sub in ast.walk(fd):
                    if hasattr(sub, "lineno"):
                        sub.lineno = node.lineno
                self.register_method(info, fd)
        if not is_dc and info.fields and "__init__" not in info.methods and base is None:
            raise Unsupported(f"classe {node.name} : déclarez un __init__ qui initialise ses champs", node)

    def field_default(self, v, t, node):
        """Défaut d'un champ de dataclass : constante, ou field(default_factory=list|dict) -> conteneur vide frais."""
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "field":
            kws = [k for k in v.keywords if k.arg not in ("compare", "repr", "hash")]  # compare=False est traité par l'appelant
            if v.args or len(kws) > 1:
                raise Unsupported("field(...) : un seul argument parmi default= / default_factory= (et compare=/repr=)", node)
            if not kws:
                return None  # field(compare=False) sans valeur par défaut : champ obligatoire
            k = kws[0]
            if k.arg == "default":
                return self.const_default(k.value, t, node)
            if k.arg == "default_factory":
                fac = k.value
                if isinstance(fac, ast.Name) and fac.id == "list" and t.kind == "list":
                    return ir.ListLit([], t)
                if isinstance(fac, ast.Name) and fac.id == "dict" and t.kind == "dict":
                    return ir.DictLit([], [], t)
                if isinstance(fac, ast.Name) and fac.id == "set" and t.kind == "set":
                    return ir.Call("set_new", [], t, "builtin")
            raise Unsupported("field(...) : seuls default=, default_factory=list|dict|set (de même type que le champ) sont supportés", node)
        return self.const_default(v, t, node)

    DUNDERS = {"__call__": (-1, None), "__post_init__": (0, "none"), "__len__": (0, "int"), "__bool__": (0, "bool"), "__neg__": (0, None), "__eq__": (1, "bool"), "__lt__": (1, "bool"),
               "__le__": (1, "bool"), "__gt__": (1, "bool"), "__ge__": (1, "bool"), "__add__": (1, None), "__sub__": (1, None),
               "__mul__": (1, None), "__truediv__": (1, None), "__floordiv__": (1, None), "__mod__": (1, None),
               "__getitem__": (1, None), "__setitem__": (2, "none"), "__contains__": (1, "bool")}

    def register_static(self, info, node, is_cm):
        """@staticmethod / @classmethod : devient une fonction de module `Classe_methode` (cls est remplacé par le nom de la classe)."""
        fd = copy.deepcopy(node)
        fd.decorator_list = []
        fd.name = f"{info.name}_{node.name}"
        if is_cm:
            if not fd.args.args or fd.args.args[0].arg != "cls":
                raise Unsupported(f"@classmethod {node.name} : le premier paramètre doit être `cls`", node)
            fd.args.args = fd.args.args[1:]
            cname = info.name

            class ClsToName(ast.NodeTransformer):
                def visit_Name(self, n):
                    return ast.copy_location(ast.Name(id=cname, ctx=n.ctx), n) if n.id == "cls" else n

            fd = ClsToName().visit(fd)
        elif fd.args.args and fd.args.args[0].arg in ("self", "cls"):
            raise Unsupported(f"@staticmethod {node.name} : pas de paramètre self/cls", node)
        self.register(fd)
        self.extra_defs.append(fd)
        info.statics[node.name] = (fd.name, is_cm, info.name)

    def lookup_static(self, cname, m):
        for info in self.chain(cname):
            if m in info.statics:
                return info.statics[m]
        return None

    def register_method(self, info, node):
        kinds, setter_of = set(), None
        for d in node.decorator_list:
            if isinstance(d, ast.Name) and d.id in ("abstractmethod", "staticmethod", "classmethod", "property"):
                kinds.add(d.id)
            elif isinstance(d, ast.Attribute) and d.attr == "setter" and isinstance(d.value, ast.Name):
                setter_of = d.value.id
            else:
                raise Unsupported(f"décorateur @{ast.unparse(d)} sur une méthode non supporté (supportés : staticmethod, classmethod, "
                                  "property, x.setter, abstractmethod)", node)
        if "staticmethod" in kinds or "classmethod" in kinds:
            if node.returns is None:
                raise Unsupported(f"annotation de retour manquante pour {info.name}.{node.name}()", node)
            return self.register_static(info, node, "classmethod" in kinds)
        a = node.args
        if not a.args or a.args[0].arg != "self":
            raise Unsupported(f"méthode {node.name} : le premier paramètre doit être `self`", node)
        n = node.name
        if setter_of is not None:
            if setter_of not in info.props:
                raise Unsupported(f"@{setter_of}.setter sans @property {setter_of} défini avant", node)
            n = f"set_prop_{setter_of}"
            info.setters.add(setter_of)
        elif n.startswith("__") and n.endswith("__") and n not in ("__init__", "__str__", "__repr__") and n not in self.DUNDERS:
            raise Unsupported(f"méthode spéciale {n} non supportée (supportées : __init__, __str__, __repr__, __len__, __bool__, __eq__, "
                              "__lt__/__le__/__gt__/__ge__, opérateurs arithmétiques, __neg__, __getitem__, __setitem__, __contains__)", node)
        if node.returns is None:
            raise Unsupported(f"annotation de retour manquante pour {info.name}.{n}()", node)
        params, defaults = self.params_and_defaults(node, skip=1)
        ret = self.ret_type(node)
        if n == "__init__" and ret != NONE:
            raise Unsupported("__init__ doit être annoté -> None", node)
        if n in ("__str__", "__repr__") and (ret != STR or params):
            raise Unsupported(f"{n} doit être `def {n}(self) -> str`", node)
        if n in self.DUNDERS:
            arity, want = self.DUNDERS[n]
            if (arity >= 0 and len(params) != arity) or (want == "int" and ret != INT) or (want == "bool" and ret != BOOL) or (want == "none" and ret != NONE):
                raise Unsupported(f"{n} : signature non supportée ({arity} paramètre(s) hors self"
                                  f"{', retour ' + want if want else ''})", node)
        if "property" in kinds:
            if params:
                raise Unsupported(f"@property {n} : pas de paramètre autre que self", node)
            info.props[n] = ret
        if setter_of is not None and (len(params) != 1 or ret != NONE or params[0][1] != info.props[setter_of]):
            raise Unsupported(f"@{setter_of}.setter : `def {setter_of}(self, valeur: T) -> None` avec le type de la propriété", node)
        if n in info.methods:
            raise Unsupported(f"méthode {info.name}.{n} définie deux fois", node)
        if info.base is not None and n != "__init__":
            up = self.lookup_method(info.base, n)
            if up is not None and ([t for _, t in up[1][0]] != [t for _, t in params] or up[1][1] != ret):
                raise Unsupported(f"méthode {info.name}.{n} : la redéfinition doit garder les types de paramètres et de retour de "
                                  f"{up[0].name}.{n}", node)
        info.methods[n] = (params, ret, defaults)
        info.nodes[n] = node

    def propagate_mutations(self, convs):
        """Un paramètre passé à une fonction qui le modifie est lui aussi modifié (point fixe)."""
        by_name = {(f"{f.owner}.{f.name}" if f.owner else f.name): f for _, f in convs}
        changed = True
        while changed:
            changed = False
            for c, f in convs:
                for callee, idx, var in c.callsites:
                    g = by_name.get(callee)
                    if g and idx < len(g.params) and g.params[idx][0] in g.mutated and var not in f.mutated:
                        f.mutated.add(var)
                        changed = True


class FuncConv(BuiltinsMixin, CollectionsMixin, ClassesMixin, StdMixin):
    def __init__(self, fe, name, params, ret, cls=None, module=False, parent=None):
        self.fe, self.name, self.ret = fe, name, ret
        self.parent = parent  # fonction englobante pour une fonction imbriquée
        self.local_funcs = {}  # nom -> (params, ret, défauts) des fonctions imbriquées déclarées ici
        self.nonlocal_names = set()
        self.local_irs = {}  # fonctions imbriquées déclarées ici -> nœud IR (pour marquer celles qui servent de valeur)
        self.calls_self = False
        self.is_module = module  # code de niveau module : ses variables sont des GLOBALES visibles des fonctions
        self.global_names = set()  # noms déclarés `global x` dans cette fonction
        self.cls = cls  # nom de la classe si c'est une méthode
        self.in_init = cls is not None and name == "__init__"
        self.params = params
        self.pnames = {p for p, _ in params}
        self.scope = fe.globals if module else dict(params)
        if cls is not None:
            self.scope["self"] = class_of(cls)
        self.loopvars = set()
        self.loop_flags = []  # un drapeau (ou None) par boucle englobante : les break d'un for/else y écrivent
        self.handler_depth = 0  # profondeur de blocs `except` (autorise `raise` seul)
        self.casts = {}  # variable -> type de classe plus précis (après `if isinstance(x, Sous):`)
        self.narrowed = set()  # variables Optional dont on sait qu'elles ne sont pas None (après `if x is not None`, `if x is None: return`...)
        self.assigned_names = set()
        self.depth = 0
        self.hoisted = []
        self.tmp = 0
        self.mutated, self.reassigned = set(), set()
        self.var_keys = {}  # variable locale -> clé de déclaration (élargissement en Optional)
        self.callsites = []
        self.allowed_gens = set()  # expressions génératrices passées directement à sum/min/max/...

    def run(self, nodes):
        body = self.block(nodes, nested=False)
        if not body and self.ret != NONE:  # méthode abstraite / stub (`...`, `pass`) : lève au lieu de « retourner None »
            body = [ir.Raise(ir.New("NotImplementedError", [], class_of("NotImplementedError")))]
        return ir.Func(self.name, self.params, self.ret, body, self.hoisted, self.mutated, self.reassigned, self.cls, self.ret.kind == "gen")

    def fresh(self, e, node, what=""):
        """Conservé pour l'historique : list et dict sont des poignées PARTAGÉES dans les deux cibles (shared_ptr en C++,
        références en Kotlin), l'alias de Python est donc reproduit exactement et plus rien n'est à refuser ici."""
        return e

    def printable(self, t, nested=False):
        """Python n'affiche un objet de façon déterministe que via __repr__ (dans un conteneur) ou __str__/__repr__ (seul)."""
        if t.kind == "class":
            info = self.fe.classes[t.args[0]]
            return (info.is_dataclass or info.is_exc or self.fe.lookup_method(info.name, "__repr__") is not None
                    or (not nested and self.fe.lookup_method(info.name, "__str__") is not None))
        if t.kind == "func":
            return False
        if t.kind == "set":  # l'ordre d'affichage d'un set de chaînes/tuples varie d'une exécution à l'autre en Python
            return t.args[0] in (INT, BOOL)
        if t.kind in ("list", "dict", "tuple", "deque", "vtuple"):
            return all(self.printable(a, True) for a in t.args)
        if t.kind == "optional":
            return self.printable(t.args[0], nested)
        return True

    def need_printable(self, e, node):
        if not self.printable(e.type):
            raise Unsupported(f"affichage d'un objet de type {e.type} non supporté : sans __str__/__repr__ (ou @dataclass), "
                              "Python afficherait une adresse mémoire non déterministe. Définissez __str__ (et __repr__ pour "
                              "l'afficher dans une liste/un tuple)", node)
        return e

    # ---------- outils ----------
    def coerce(self, e, to, node):
        """Types identiques exigés. Python ne convertit PAS un int en float quand on l'affecte, le passe en argument
        ou le retourne (x: float = 3 garde un int : print(x) affiche 3). On refuse plutôt que d'afficher 3.0."""
        if e.type == to:
            return e
        to_r = self.fe.resolve(to)
        if e.type.kind == "gen" and to_r.kind == "list" and self.fe.unify(list_of(e.type.args[0]), to_r):
            return ir.Call("gen_list", [e], to_r, "builtin")  # Iterable[T] reçoit un générateur : consommé en liste
        if self.fe.sub_ok(e.type, to_r):  # sous-classe -> classe parente (conversion implicite de shared_ptr / référence)
            return e
        if to_r.kind == "optional":  # T / None -> Optional[T]
            inner = to_r.args[0]
            if e.type == NONE:
                return ir.NoneOf(to_r)
            if e.type.kind == "optional":
                if self.fe.unify(e.type.args[0], inner) or self.fe.sub_ok(e.type.args[0], inner):
                    return e
            elif self.fe.unify(e.type, inner) or self.fe.sub_ok(e.type, inner):
                return ir.Wrap(e, to_r)
            elif e.type == INT and inner == FLOAT and not self.fe.strict:
                self.fe.warn("int utilisé là où Optional[float] est annoté : converti en float", node)
                return ir.Wrap(ir.Cast(e, FLOAT), to_r)
            raise Unsupported(f"type incompatible : {e.type} fourni, {to} attendu", node)
        if e.type.kind == "optional" and to_r.kind != "pending":  # Optional[T] -> T : vérifié à l'exécution (None -> exception)
            if self.fe.unify(e.type.args[0], to):
                return ir.Unwrap(e, self.fe.resolve(e.type.args[0]))
            raise Unsupported(f"type incompatible : {e.type} fourni, {to} attendu", node)
        if e.type == NONE:
            raise Unsupported(f"None fourni là où {to} est attendu (annotez le type Optional[...] / `... | None`)", node)
        if self.fe.unify(e.type, to):  # type en attente (littéral vide) : l'usage révèle son type
            return e
        if e.type == INT and to == FLOAT:
            if self.fe.strict:
                raise Unsupported("un int n'est pas converti en float par Python à l'affectation/au passage d'argument/au retour "
                                  "(print afficherait 3, pas 3.0) : écrivez une constante flottante (3.0) ou float(...)", node)
            self.fe.warn("int utilisé là où float est annoté : converti en float (Python conserve un int : un affichage direct "
                         "donnerait 3 au lieu de 3.0)", node)
            return ir.Cast(e, FLOAT)
        raise Unsupported(f"type incompatible : {e.type} fourni, {to} attendu", node)

    def unopt(self, e):
        """Optional[T] utilisé là où un T est nécessaire : vérification à l'exécution (None lève l'erreur de Python)."""
        return ir.Unwrap(e, self.fe.resolve(e.type.args[0])) if e.type.kind == "optional" else e

    def widen_request(self, key, t, value):
        """Affecter None (ou un Optional) à une variable/un champ de type T : on le demande à la passe suivante."""
        if self.fe.dry and t.kind != "optional" and (value.type == NONE or value.type.kind == "optional"):
            tok = ("widen", key)
            if tok not in self.fe.hints:
                self.fe.hints[tok] = True
                self.fe.changed = True

    @staticmethod
    def promote(e):
        """Promotion int -> float, valable UNIQUEMENT dans l'arithmétique et les comparaisons (là, Python promeut aussi)."""
        return ir.Cast(e, FLOAT) if e.type == INT else e

    def note_mutation(self, e):
        v = root_var(e)
        if v and v.name in self.pnames and is_container(v.type):
            self.mutated.add(v.name)

    def truthy(self, e):
        t = e.type
        if t == BOOL:
            return e
        if t.kind == "optional":
            if not self.is_pure(e):
                raise Unsupported("test de vérité sur une valeur Optional non simple : comparez explicitement `is not None`")
            inner = t.args[0]
            notnone = ir.IsNone(e, True)
            if inner.kind == "class":  # un objet est toujours « vrai » (pas de __bool__/__len__)
                return notnone
            return ir.BoolOp("and", [notnone, self.truthy(ir.Unwrap(e, inner))])
        if t.kind == "class":
            c = t.args[0]
            if self.fe.lookup_method(c, "__bool__") is not None:
                return ir.UserMethodCall(e, c, "__bool__", [], BOOL)
            if self.fe.lookup_method(c, "__len__") is not None:
                return ir.Cmp(">", ir.UserMethodCall(e, c, "__len__", [], INT), ir.Const(0, INT))
            return ir.Const(True, BOOL)
        if t == INT:
            return ir.Cmp("!=", e, ir.Const(0, INT))
        if t == FLOAT:
            return ir.Cmp("!=", e, ir.Const(0.0, FLOAT))
        if t == STR or is_container(t):
            return ir.Cmp(">", ir.Call("len", [e], INT, "builtin"), ir.Const(0, INT))
        raise Unsupported(f"valeur de vérité non supportée pour le type {t}")

    def bool_operands(self, node, conv):
        """Opérandes d'un and/or : chacun est converti en sachant ce que les précédents ont établi (isinstance, is not None)."""
        is_and = isinstance(node.op, ast.And)
        vals, pos, casts = [], set(), {}
        for v in node.values:
            vals.append(self.scoped(lambda v=v: conv(v), set(pos), dict(casts)))
            pos |= self.narrow_set(v, is_and)
            casts.update(self.cast_set(v, is_and))
        return vals

    def cond(self, node):
        if isinstance(node, ast.BoolOp):
            op = "and" if isinstance(node.op, ast.And) else "or"
            return ir.BoolOp(op, self.bool_operands(node, self.cond))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return ir.Unary("not", self.cond(node.operand), BOOL)
        return self.truthy(self.expr(node))

    # ---------- blocs et instructions ----------
    def scoped(self, fn, add=(), casts=None):
        """Convertit un bloc avec `add` (variables sûres non-None) et `casts` (variable -> sous-classe prouvée par isinstance) ;
        à la sortie, le savoir acquis dans le bloc est oublié, et ce qui y a été réaffecté n'est plus considéré comme sûr."""
        saved, saved_a, saved_c = self.narrowed, self.assigned_names, self.casts
        self.narrowed, self.assigned_names = set(saved) | set(add), set()
        self.casts = {**saved_c, **(casts or {})}
        try:
            r = fn()
        finally:
            assigned = self.assigned_names
            self.narrowed, self.assigned_names = saved - assigned, saved_a | assigned
            self.casts = {k: v for k, v in saved_c.items() if k not in assigned}
        return r

    def cast_set(self, t, positive):
        """Variables dont `isinstance(x, Sous)` prouve le type plus précis quand la condition vaut `positive`."""
        if isinstance(t, ast.Call) and isinstance(t.func, ast.Name) and t.func.id == "isinstance" and positive \
                and len(t.args) == 2 and isinstance(t.args[0], ast.Name) and isinstance(t.args[1], ast.Name):
            n, c = t.args[0].id, t.args[1].id
            if n in self.scope and n not in self.fe.globals and c in self.fe.classes and c not in self.scope:
                st = self.fe.resolve(self.scope[n])
                st = st.args[0] if st.kind == "optional" else st
                if st.kind == "class" and self.fe.is_subclass(c, st.args[0]):
                    return {n: class_of(c)}
            return {}
        if isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not):
            return self.cast_set(t.operand, not positive)
        if isinstance(t, ast.BoolOp) and isinstance(t.op, ast.And) == positive:
            out = {}
            for v in t.values:
                out.update(self.cast_set(v, positive))
            return out
        return {}

    def narrow_set(self, t, positive):
        """Variables locales Optional prouvées non-None quand la condition `t` vaut `positive`."""
        names = set()
        if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.left, ast.Name)                 and isinstance(t.comparators[0], ast.Constant) and t.comparators[0].value is None:
            op = t.ops[0]
            if (isinstance(op, (ast.IsNot, ast.NotEq)) and positive) or (isinstance(op, (ast.Is, ast.Eq)) and not positive):
                names = {t.left.id}
        elif isinstance(t, ast.Name) and positive:
            names = {t.id}
        elif isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not):
            names = self.narrow_set(t.operand, not positive)
        elif isinstance(t, ast.BoolOp) and isinstance(t.op, ast.And) == positive:
            for v in t.values:
                names |= self.narrow_set(v, positive)
        return {n for n in names if n in self.scope and n not in self.fe.globals and self.fe.resolve(self.scope[n]).kind == "optional"}

    @staticmethod
    def stored_names(nodes):
        return {n.id for st in nodes for n in ast.walk(st) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}

    @staticmethod
    def terminates(nodes):
        return bool(nodes) and isinstance(nodes[-1], (ast.Return, ast.Raise, ast.Continue, ast.Break))

    def block(self, nodes, nested=True):
        return self.scoped(lambda: self.block_(nodes, nested))

    def block_(self, nodes, nested=True):
        if nested:
            self.depth += 1
        out = []
        for n in nodes:
            if self.fe.dry:  # passe à blanc : on explore le plus possible, une instruction non convertible est ignorée
                try:
                    out.extend(self.stmt(n))
                except Unsupported:
                    pass
            else:
                out.extend(self.stmt(n))
        if nested:
            self.depth -= 1
        return out

    def stmt(self, node):
        m = getattr(self, "s_" + type(node).__name__, None)
        if m is None:
            raise Unsupported(f"instruction non supportée : {type(node).__name__}", node)
        return m(node)

    def s_Pass(self, node):
        return []

    def s_Global(self, node):
        for n in node.names:
            if n not in self.fe.globals:
                raise Unsupported(f"`global {n}` : variable globale inconnue (définissez-la au niveau du module avant les fonctions)", node)
            self.global_names.add(n)
        return []

    def s_Break(self, node):
        flag = self.loop_flags[-1] if self.loop_flags else None
        if flag is not None:  # for ... else : un break annule la clause else
            return [ir.Assign(ir.Var(flag, BOOL), ir.Const(False, BOOL)), ir.Break()]
        return [ir.Break()]

    def loop_with_else(self, node, convert):
        """for/while ... else : l'else s'exécute si la boucle se termine sans break (drapeau remis à faux par chaque break)."""
        flag, pre = None, []
        if node.orelse:
            flag = f"__ne{self.tmp}"
            self.tmp += 1
            pre = [ir.VarDecl(flag, BOOL, ir.Const(True, BOOL))]
        self.loop_flags.append(flag)
        try:
            out = convert()
        finally:
            self.loop_flags.pop()
        if flag is None:
            return out
        return pre + out + [ir.If(ir.Var(flag, BOOL), self.block(node.orelse), [])]

    def s_Continue(self, node):
        return [ir.Continue()]

    def s_Expr(self, node):
        v = node.value
        if isinstance(v, ast.Yield):
            if self.ret.kind != "gen" or v.value is None:
                raise Unsupported("yield : seulement `yield valeur` dans une fonction génératrice", node)
            et = self.ret.args[0]
            return [ir.Yield(self.coerce(self.expr(v.value, et), et, node))]
        if isinstance(v, ast.YieldFrom):  # yield from it  ==  for x in it: yield x
            name = f"__yf{self.tmp}"
            self.tmp += 1
            loop = ast.For(target=ast.Name(id=name, ctx=ast.Store()), iter=v.value,
                           body=[ast.Expr(value=ast.Yield(value=ast.Name(id=name, ctx=ast.Load())))], orelse=[])
            return self.stmt(ast.fix_missing_locations(ast.copy_location(loop, node)))
        if isinstance(v, ast.Constant):
            return []  # docstring
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "print":
            sep = end = None
            err = False
            for kw in v.keywords:
                if kw.arg in ("sep", "end"):
                    val = self.coerce(self.expr(kw.value), STR, node)
                    if kw.arg == "sep":
                        sep = val
                    else:
                        end = val
                elif kw.arg == "file":
                    if isinstance(kw.value, ast.Attribute) and self.module_of(kw.value.value) == "sys" and kw.value.attr in ("stderr", "stdout"):
                        err = kw.value.attr == "stderr"
                    else:
                        raise Unsupported("print(file=...) : seulement sys.stdout / sys.stderr", node)
                elif kw.arg == "flush":
                    pass
                else:
                    raise Unsupported(f"print({kw.arg}=...) non supporté", node)
            if len(v.args) == 1 and isinstance(v.args[0], ast.Starred):  # print(*xs, sep=...) = print(sep.join(map(str, xs)))
                xs = self.as_list(self.unopt(self.expr(v.args[0].value, view_ok=True)))
                if xs.type.kind != "list":
                    raise Unsupported(f"print(*x) : liste attendue, pas {xs.type}", node)
                self.need_printable(ir.Var("__x", xs.type.args[0]), node)
                return [ir.Print([ir.Call("join_star", [xs, sep if sep is not None else ir.Const(" ", STR)], STR, "builtin")], None, end, err)]
            if any(isinstance(a, ast.Starred) for a in v.args):
                raise Unsupported("print(a, *xs, b) : le *étoile doit être l'unique argument", node)
            return [ir.Print([self.need_printable(self.expr(a), node) for a in v.args], sep, end, err)]
        if isinstance(v, ast.Call):
            lowered = self.shuffle_stmt(v)
            if lowered is not None:
                return lowered
        e = self.expr(v)
        if not isinstance(e, (ir.Call, ir.MethodCall, ir.UserMethodCall, ir.New, ir.KeyOp, ir.SuperCall, ir.CallVal)):
            raise Unsupported("expression sans effet", node)
        return [ir.ExprStmt(e)]

    def s_Return(self, node):
        if self.ret.kind == "gen":
            if node.value is not None and not (isinstance(node.value, ast.Constant) and node.value.value is None):
                raise Unsupported("return avec valeur dans un générateur non supporté", node)
            return [ir.Return(None)]
        if self.in_init:
            raise Unsupported("return dans __init__ non supporté", node)
        if node.value is None or (isinstance(node.value, ast.Constant) and node.value.value is None):
            if self.ret.kind == "optional":
                return [ir.Return(ir.NoneOf(self.ret))]
            if self.ret != NONE:
                raise Unsupported(f"return sans valeur dans une fonction qui retourne {self.ret}", node)
            return [ir.Return(None)]
        if self.ret == NONE:
            raise Unsupported("return avec valeur dans une fonction annotée -> None", node)
        return [ir.Return(self.coerce(self.expr(node.value, self.ret), self.ret, node))]

    def s_If(self, node):
        c = self.cond(node.test)
        pos, neg = self.narrow_set(node.test, True), self.narrow_set(node.test, False)
        cpos, cneg = self.cast_set(node.test, True), self.cast_set(node.test, False)
        body = self.scoped(lambda: self.block(node.body), pos, cpos)
        orelse = self.scoped(lambda: self.block(node.orelse), neg, cneg) if node.orelse else []
        # `if x is None: return` : la suite du bloc sait que x n'est pas None (sauf si une branche l'a réaffecté)
        if self.terminates(node.body):
            self.narrowed |= neg - self.stored_names(node.orelse)
            self.casts.update({k: v for k, v in cneg.items() if k not in self.stored_names(node.orelse)})
        if node.orelse and self.terminates(node.orelse):
            self.narrowed |= pos - self.stored_names(node.body)
            self.casts.update({k: v for k, v in cpos.items() if k not in self.stored_names(node.body)})
        return [ir.If(c, body, orelse)]

    def s_While(self, node):
        return self.loop_with_else(node, lambda: self.s_While_(node))

    def s_While_(self, node):
        stored = self.stored_names(node.body)  # réaffecté dans la boucle : plus sûr d'une itération à l'autre
        self.narrowed -= stored
        self.casts = {k: v for k, v in self.casts.items() if k not in stored}
        c = self.cond(node.test)
        return [ir.While(c, self.scoped(lambda: self.block(node.body), self.narrow_set(node.test, True), self.cast_set(node.test, True)))]

    def s_AugAssign(self, node):
        op = BINOPS.get(type(node.op))
        if op is None:
            raise Unsupported(f"opérateur non supporté : {type(node.op).__name__}", node)
        target = self.target_expr(node.target)
        val = self.expr(node.value)
        if target.type.kind == "set" and op in ("|", "&", "-", "^"):  # modification EN PLACE (alias visibles), comme en Python
            if not self.fe.unify(self.unopt(val).type, target.type):
                raise Unsupported(f"opérateur {op}= entre {target.type} et {val.type}", node)
            name = {"|": "set_ior", "&": "set_iand", "-": "set_isub", "^": "set_ixor"}[op]
            self.note_mutation(target)
            return [ir.ExprStmt(ir.Call(name, [target, self.unopt(val)], NONE, "builtin"))]
        return self.assign_to(node.target, self.binop(op, target, val, node), node)

    def s_AnnAssign(self, node):
        if isinstance(node.target, ast.Attribute):  # self.x: int = ... (déclare un champ dans __init__)
            if node.value is None:
                raise Unsupported("déclaration d'un champ sans valeur : écrivez self.x: int = ...", node)
            t = parse_type(node.annotation, self.fe.type_names)
            return self.assign_to(node.target, self.coerce(self.expr(node.value, t), t, node), node, declared=t)
        if not isinstance(node.target, ast.Name):
            raise Unsupported("annotation sur une cible autre qu'une variable", node)
        t = parse_type(node.annotation, self.fe.type_names)
        if node.value is None:
            return self.declare(node.target.id, t, None, node)
        v = self.coerce(self.expr(node.value, t), t, node)
        return self.assign_to(node.target, v, node, declared=t)

    def s_Assign(self, node):
        if len(node.targets) != 1:  # a = b = valeur : la valeur est évaluée UNE fois, affectée de gauche à droite
            out = []
            v = self.expr(node.value)
            if not self.is_pure(v):
                v = self.temp(v, out)
            for t in node.targets:
                out.extend(self.unpack(t, v, node))
            return out
        tgt = node.targets[0]
        if isinstance(tgt, ast.Tuple):
            if isinstance(node.value, ast.Tuple) and len(node.value.elts) == len(tgt.elts):
                # a, b = x, y : tout le côté droit est évalué AVANT les affectations (échange a, b = b, a)
                out, temps = [], []
                for v in node.value.elts:
                    e = self.expr(v)
                    temps.append(self.temp(e, out))
                for t, tv in zip(tgt.elts, temps):
                    out.extend(self.unpack(t, tv, node))
                return out
            return self.unpack(tgt, self.expr(node.value), node)
        exp = None
        if isinstance(tgt, ast.Name) and tgt.id in self.scope:
            exp = self.scope[tgt.id]
        elif isinstance(tgt, ast.Subscript):
            exp = self.target_expr(tgt).type
        elif isinstance(tgt, ast.Attribute):
            exp = self.field_type(tgt)  # None si le champ n'existe pas encore (créé par self.x = ... dans __init__)
        return self.assign_to(tgt, self.expr(node.value, exp), node)

    def field_type(self, tgt):
        if isinstance(tgt.value, ast.Name) and tgt.value.id in self.fe.classes and tgt.value.id not in self.scope:
            g = self.fe.lookup_classvar(tgt.value.id, tgt.attr)  # Classe.variable : type de la globale
            gt = self.fe.globals.get(g) or self.fe.pre_globals.get(g) if g else None
            return self.fe.resolve(gt) if gt is not None else None
        base = self.obj_expr(tgt.value)
        if base.type.kind == "class":
            f = self.fe.lookup_field(base.type.args[0], tgt.attr)
            return f[1][0] if f else None
        return None

    def temp(self, e, out):
        """Range e dans une variable temporaire (déclarée en place) et renvoie cette variable."""
        name = f"__t{self.tmp}"
        self.tmp += 1
        out.append(ir.VarDecl(name, e.type, e))
        return ir.Var(name, e.type)

    def unpack(self, tgt, value, node):
        """Affecte `value` à la cible `tgt` ; si c'est un tuple de cibles (a, b) ou ((a, b), c), dépaquette récursivement."""
        if not isinstance(tgt, ast.Tuple):
            return self.assign_to(tgt, value, node)
        if any(isinstance(e, ast.Starred) for e in tgt.elts):
            return self.star_unpack(tgt, value, node)
        if value.type.kind == "class" and self.fe.classes[value.type.args[0]].is_namedtuple:
            flds = list(self.fe.classes[value.type.args[0]].fields.items())
            if len(flds) != len(tgt.elts):
                raise Unsupported(f"dépaquetage : {len(tgt.elts)} cibles mais {value.type} a {len(flds)} champs", node)
            out = []
            base = value if isinstance(value, ir.Var) else self.temp(value, out)
            for sub, (fname, (ft, _)) in zip(tgt.elts, flds):
                out.extend(self.unpack(sub, ir.Attr(base, fname, ft), node))
            return out
        if value.type.kind != "tuple" or len(value.type.args) != len(tgt.elts):
            raise Unsupported(f"dépaquetage : {len(tgt.elts)} cibles mais la valeur est de type {value.type}", node)
        out = []
        base = value if isinstance(value, ir.Var) else self.temp(value, out)
        for i, sub in enumerate(tgt.elts):
            out.extend(self.unpack(sub, ir.TupleGet(base, i, value.type.args[i]), node))
        return out

    def star_unpack(self, tgt, value, node):
        """a, *milieu, z = xs (liste) : réécrit en affectations par indices/tranche, avec le contrôle de longueur de Python."""
        if value.type.kind != "list":
            raise Unsupported(f"dépaquetage étoilé : une liste est attendue, pas {value.type}", node)
        stars = [i for i, e in enumerate(tgt.elts) if isinstance(e, ast.Starred)]
        if len(stars) != 1:
            raise Unsupported("un seul *cible est permis", node)
        k, n = stars[0], len(tgt.elts)
        out = []
        base = value if isinstance(value, ir.Var) else self.temp(value, out)
        name = base.name
        self.scope.setdefault(name, base.type)
        loc = lambda x: ast.copy_location(x, node)  # noqa: E731
        src = ast.parse(f"{name}").body[0].value
        need = n - 1
        chk = ast.parse(f"if len({name}) < {need}:\n    raise ValueError('not enough values to unpack (expected at least {need}, got ' + str(len({name})) + ')')").body[0]
        stmts = [chk]
        for i, e in enumerate(tgt.elts):
            if i < k:
                rhs = ast.parse(f"{name}[{i}]", mode="eval").body
            elif i == k:
                after = n - 1 - k
                rhs = ast.parse(f"{name}[{k}:len({name}) - {after}]" if after else f"{name}[{k}:]", mode="eval").body
                e = e.value
            else:
                rhs = ast.parse(f"{name}[{i - n}]", mode="eval").body
            stmts.append(ast.Assign(targets=[e], value=rhs))
        for st in stmts:
            ast.fix_missing_locations(loc(st))
            for sub in ast.walk(st):
                if hasattr(sub, "lineno"):
                    sub.lineno = node.lineno
            out.extend(self.stmt(st))
        return out

    def target_expr(self, tgt):
        if isinstance(tgt, ast.Name):
            if tgt.id in self.nonlocal_names:
                return ir.Var(tgt.id, self.fe.resolve(self.outer_var(tgt.id)))
            if tgt.id in self.global_names and tgt.id in self.fe.globals:
                return ir.Var(tgt.id, self.fe.resolve(self.fe.globals[tgt.id]))
            if tgt.id not in self.scope:
                raise Unsupported(f"variable '{tgt.id}' utilisée avant son affectation", tgt)
            return ir.Var(tgt.id, self.fe.resolve(self.scope[tgt.id]))
        if isinstance(tgt, ast.Subscript):
            return self.index(tgt)
        if isinstance(tgt, ast.Attribute):
            return self.e_Attribute(tgt)
        raise Unsupported(f"cible d'affectation non supportée : {type(tgt).__name__}", tgt)

    def declare(self, name, t, value, node):
        if name in self.scope or name in self.loopvars:
            raise Unsupported(f"variable '{name}' déjà déclarée", node)
        self.scope[name] = t
        if self.is_module:  # variable globale : déclarée au niveau du fichier, affectée à sa position dans l'ordre d'exécution
            return [ir.Assign(ir.Var(name, t), value)] if value is not None else []
        if self.depth == 0:
            return [ir.VarDecl(name, t, value)]
        if any(h == name for h, _ in self.hoisted):
            if (name, t) not in self.hoisted:
                raise Unsupported(f"variable '{name}' réutilisée avec un autre type ({t}) : utilisez un autre nom", node)
        else:
            self.hoisted.append((name, t))
        return [ir.Assign(ir.Var(name, t), value)] if value is not None else []

    def assign_to(self, tgt, value, node, declared=None):
        if isinstance(tgt, ast.Name):
            self.narrowed.discard(tgt.id)
            self.casts.pop(tgt.id, None)
            self.assigned_names.add(tgt.id)
        if value.type == NONE and not (isinstance(value, ir.Const) and value.value is None):
            raise Unsupported("affectation du résultat d'un appel sans valeur de retour", node)
        if isinstance(tgt, ast.Attribute):
            return self.assign_attr(tgt, value, node, declared)
        if isinstance(tgt, ast.Name):
            name = tgt.id
            if name == "self" and self.cls is not None:
                raise Unsupported("réaffectation de self non supportée", node)
            if name in self.loopvars:
                raise Unsupported(f"modification de la variable de boucle '{name}'", node)
            if name in self.nonlocal_names:
                ot = self.fe.resolve(self.outer_var(name))
                return [ir.Assign(ir.Var(name, ot), self.coerce(value, ot, node))]
            if name in self.global_names:
                gt = self.fe.resolve(self.fe.globals[name])
                self.widen_request(self.fe.global_keys.get(name), gt, value)
                return [ir.Assign(ir.Var(name, gt), self.coerce(value, gt, node))]
            if name in self.scope:
                t = self.fe.resolve(self.scope[name])
                if name in self.pnames:
                    self.reassigned.add(name)  # les paramètres sont des poignées : rebinder la variable locale n'affecte pas l'appelant
                else:
                    self.widen_request(self.var_keys.get(name) or self.fe.global_keys.get(name), t, value)
                try:
                    v2 = self.coerce(value, t, node)
                except Unsupported as ex:
                    if value.type != t and not self.fe.dry:
                        base_msg = re.sub(r"^ligne [0-9]+ : ", "", str(ex))
                        raise Unsupported(f"{base_msg} -- la variable '{name}' est déjà de type {t} : Python autorise "
                                          "à la réaffecter avec un autre type, pas ce convertisseur (utilisez un autre nom)", node)
                    raise
                return [ir.Assign(ir.Var(name, t), v2)]
            key = ("var", name, node.lineno, node.col_offset)
            if declared is None and value.type == NONE:  # x = None : Optional[?], le type vient des affectations suivantes
                t = optional_of(self.empty_hint(node, "opt"))
            else:
                t = self.fe.widened(key, declared or value.type)
            (self.fe.global_keys if self.is_module else self.var_keys)[name] = key
            return self.declare(name, t, self.coerce(value, t, node), node)
        if isinstance(tgt, ast.Subscript) and isinstance(tgt.slice, ast.Slice):
            base = self.expr(tgt.value)
            if base.type.kind != "list":
                raise Unsupported("affectation de tranche : listes seulement", node)
            if not self.fe.unify(value.type, base.type):
                raise Unsupported(f"affectation de tranche : liste de même type ({base.type}) attendue, pas {value.type}", node)
            lo, hi, step = self.slice_parts(tgt.slice, node)
            return [ir.SliceAssign(base, lo, hi, step, value)]
        if isinstance(tgt, ast.Subscript):
            target = self.index(tgt)
            if isinstance(target, ir.UserMethodCall) and target.name == "__getitem__":
                f = self.fe.lookup_method(target.cls, "__setitem__")
                if f is None:
                    raise Unsupported(f"affectation par indice non définie pour {target.obj.type} (définissez __setitem__)", node)
                params = f[1][0]
                return [ir.ExprStmt(ir.UserMethodCall(target.obj, target.cls, "__setitem__",
                                                      [target.args[0], self.coerce(value, params[1][1], node)], NONE))]
            if isinstance(target, ir.TupleGet):
                raise Unsupported("les tuples sont immuables : t[i] = ... est interdit", node)
            self.note_mutation(target)
            return [ir.Assign(target, self.coerce(value, target.type, node))]
        raise Unsupported(f"cible d'affectation non supportée : {type(tgt).__name__}", node)

    def assign_attr(self, tgt, value, node, declared=None):
        """obj.champ = valeur. Dans __init__, `self.champ = ...` DÉCLARE le champ (type inféré ou annoté)."""
        if isinstance(tgt.value, ast.Name) and tgt.value.id in self.fe.classes and tgt.value.id not in self.scope:
            g = self.fe.lookup_classvar(tgt.value.id, tgt.attr)  # Classe.variable = valeur : modifie la globale qui la porte
            if g is None:
                raise Unsupported(f"{tgt.value.id}.{tgt.attr} : variable de classe inconnue", node)
            gt = self.fe.resolve(self.fe.globals.get(g) or self.fe.pre_globals.get(g))
            return [ir.Assign(ir.Var(g, gt), self.coerce(value, gt, node))]
        base = self.obj_expr(tgt.value)
        if base.type.kind != "class":
            raise Unsupported(f"affectation d'un attribut sur le type {base.type} non supportée", node)
        info = self.fe.classes[base.type.args[0]]
        name = tgt.attr
        pt = self.fe.lookup_prop(info.name, name)
        if pt is not None:
            if not self.fe.has_setter(info.name, name):
                raise Unsupported(f"la propriété {info.name}.{name} n'a pas de setter (en Python : AttributeError)", node)
            return [ir.ExprStmt(ir.UserMethodCall(base, info.name, f"set_prop_{name}", [self.coerce(value, pt, node)], NONE))]
        is_self = isinstance(tgt.value, ast.Name) and tgt.value.id == "self"
        if info.frozen:
            raise Unsupported(f"dataclass figée (frozen=True) : le champ '{name}' ne peut pas être modifié", node)
        found = self.fe.lookup_field(info.name, name)
        if found is not None:
            ft = found[1][0]
            if declared is not None and declared != ft:
                raise Unsupported(f"champ '{name}' redéclaré avec un autre type ({declared} au lieu de {ft})", node)
        elif self.fe.lookup_classvar(info.name, name) is not None:
            raise Unsupported(f"{info.name}.{name} est une variable de classe : l'affecter via une instance créerait un attribut "
                              f"d'instance distinct en Python ; écrivez {info.name}.{name} = ...", node)
        elif self.in_init and is_self and not info.is_dataclass:
            if declared is None and value.type == NONE:
                ft = optional_of(self.empty_hint(node, "opt"))  # self.x = None : Optional[?] précisé par les affectations suivantes
            else:
                ft = self.fe.widened(("field", info.name, name), declared or value.type)
            info.fields[name] = (ft, None)
        else:
            raise Unsupported(f"champ '{name}' inconnu sur {info.name} : déclarez-le dans le corps de la classe "
                              "(x: int) ou par self.x = ... dans __init__", node)
        ft = self.fe.resolve(ft)
        self.widen_request(("field", info.name, name), ft, value)
        return [ir.Assign(ir.Attr(base, name, ft), self.coerce(value, ft, node))]

    def s_For(self, node):
        return self.loop_with_else(node, lambda: self.s_For_(node))

    def s_For_(self, node):
        stored = self.stored_names(node.body)
        self.narrowed -= stored
        self.casts = {k: v for k, v in self.casts.items() if k not in stored}
        it = node.iter
        if isinstance(node.target, ast.Tuple):
            return self.for_unpack(node)
        if not isinstance(node.target, ast.Name):
            raise Unsupported("cible de boucle non supportée", node)
        name = node.target.id
        if name in self.scope:
            raise Unsupported(f"la variable de boucle '{name}' est déjà utilisée comme variable ailleurs : renommez-la", node)
        rng = self.range_args(it, node)
        if rng is not None:
            start, stop, step = rng
            self.scope[name] = INT
            self.loopvars.add(name)
            body = self.block(node.body)
            self.loopvars.discard(name)
            del self.scope[name]
            return [ir.ForRange(name, start, stop, step, body)]
        iterable, elem = self.iterable(it, node)
        self.scope[name] = elem
        self.loopvars.add(name)
        body = self.block(node.body)
        self.loopvars.discard(name)
        del self.scope[name]
        return [ir.ForEach(name, iterable, elem, body)]

    def range_args(self, it, node):
        """range(...) -> (début, fin, pas constant), ou None si `it` n'est pas un appel à range."""
        if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range"):
            return None
        args = [self.coerce_int(self.expr(a), a) for a in it.args]
        if not 1 <= len(args) <= 3 or it.keywords:
            raise Unsupported("range() attend 1 à 3 arguments", node)
        start = args[0] if len(args) >= 2 else ir.Const(0, INT)
        stop = args[1] if len(args) >= 2 else args[0]
        step = 1
        if len(args) == 3:
            step = self.const_int(it.args[2])
            if step is None:  # pas calculé à l'exécution : le sens de la boucle dépend de son signe
                step = args[2]
            elif step == 0:
                raise Unsupported("range() avec un pas nul", node)
        return start, stop, step

    # ---------- compréhensions ----------
    MISSING = object()

    def bind_local(self, name, t, bound):
        """Variable locale d'une compréhension : masque temporairement une éventuelle variable de même nom (portée Python 3)."""
        bound.append((name, self.scope.get(name, self.MISSING)))
        self.scope[name] = t

    def unbind(self, bound):
        for name, old in reversed(bound):
            if old is self.MISSING:
                self.scope.pop(name, None)
            else:
                self.scope[name] = old

    def local_unpack(self, tgt, value, bound):
        """Cible `for a, (b, c) in ...` d'une compréhension : variables locales déclarées en place (jamais hissées en tête de fonction)."""
        if isinstance(tgt, ast.Name):
            self.bind_local(tgt.id, value.type, bound)
            return [ir.VarDecl(tgt.id, value.type, value)]
        if not isinstance(tgt, ast.Tuple) or any(isinstance(e, ast.Starred) for e in tgt.elts):
            raise Unsupported("cible de compréhension non supportée", tgt)
        if value.type.kind != "tuple" or len(value.type.args) != len(tgt.elts):
            raise Unsupported(f"dépaquetage : {len(tgt.elts)} cibles mais la valeur est de type {value.type}", tgt)
        out = []
        for i, sub in enumerate(tgt.elts):
            out.extend(self.local_unpack(sub, ir.TupleGet(value, i, value.type.args[i]), bound))
        return out

    def comp(self, node, kind, expected):
        res = f"__c{self.tmp}"
        self.tmp += 1
        info = {}
        body = self.comp_loops(node, 0, res, kind, expected, info)
        return ir.Comp(res, info["type"], body)

    def comp_loops(self, node, i, res, kind, expected, info):
        if i == len(node.generators):
            return self.comp_leaf(node, res, kind, expected, info)
        g = node.generators[i]
        if g.is_async:
            raise Unsupported("compréhension asynchrone non supportée", node)
        bound = []
        rng = self.range_args(g.iter, node) if isinstance(g.target, ast.Name) else None
        if rng is not None:
            self.bind_local(g.target.id, INT, bound)
            loop = lambda inner: ir.ForRange(g.target.id, rng[0], rng[1], rng[2], inner)  # noqa: E731
            pre = []
        else:
            iterable, elem = self.iterable(g.iter, node)
            if isinstance(g.target, ast.Name):
                self.bind_local(g.target.id, elem, bound)
                var, pre = g.target.id, []
            else:
                var = f"__t{self.tmp}"
                self.tmp += 1
                pre = self.local_unpack(g.target, ir.Var(var, elem), bound)
            loop = lambda inner: ir.ForEach(var, iterable, elem, inner)  # noqa: E731
        conds = [self.cond(c) for c in g.ifs]  # converties avec les variables de cette boucle liées
        body = self.comp_loops(node, i + 1, res, kind, expected, info)
        for c in reversed(conds):
            body = [ir.If(c, body, [])]
        self.unbind(bound)
        return [loop(pre + body)]

    def comp_leaf(self, node, res, kind, expected, info):
        if kind == "list":
            et = expected.args[0] if expected is not None and expected.kind == "list" else None
            e = self.fresh(self.expr(node.elt, et), node)
            if et is not None:
                e = self.coerce(e, et, node)
            info["type"] = list_of(e.type)
            return [ir.ExprStmt(ir.MethodCall(ir.Var(res, info["type"]), "append", [e], NONE))]
        kt, vt = expected.args if expected is not None and expected.kind == "dict" else (None, None)
        k = self.expr(node.key, kt)
        v = self.fresh(self.expr(node.value, vt), node)
        if kt is not None:
            k, v = self.coerce(k, kt, node), self.coerce(v, vt, node)
        if not is_hashable(k.type):
            raise Unsupported(f"clé de dict de type {k.type} non supportée", node)
        info["type"] = dict_of(k.type, v.type)
        return [ir.Assign(ir.Index(ir.Var(res, info["type"]), k, v.type), v)]

    def e_ListComp(self, node, expected=None):
        return self.comp(node, "list", expected)

    def e_DictComp(self, node, expected=None):
        return self.comp(node, "dict", expected)

    def e_GeneratorExp(self, node, expected=None):
        if node not in self.allowed_gens:
            raise Unsupported("expression génératrice utilisable seulement comme argument de sum/min/max/any/all/sorted/list "
                              "(en Python c'est un itérateur paresseux ; pour une liste, écrivez [... for ...])", node)
        return self.comp(node, "list", None)

    # ---------- fonctions clé : key=lambda x: ..., key=len, key=str.lower, key=une_fonction ----------
    def sort_options(self, node, et):
        kws = {k.arg: k.value for k in node.keywords}
        if set(kws) - {"key", "reverse"}:
            raise Unsupported(f"seuls key= et reverse= sont supportés ({', '.join(sorted(set(kws) - {'key', 'reverse'}))} refusé)", node)
        key = None
        if "key" in kws and not (isinstance(kws["key"], ast.Constant) and kws["key"].value is None):
            key = self.key_lambda(kws["key"], et, node)
        rev = self.coerce(self.expr(kws["reverse"]), BOOL, node) if "reverse" in kws else ir.Const(False, BOOL)
        return key, rev

    def identity(self, et, node):
        if not is_orderable(et):
            raise Unsupported(f"tri de {et} sans key= non supporté", node)
        return ir.Lambda("__ident", et, ir.Var("__ident", et))

    def key_lambda(self, knode, et, node):
        if isinstance(knode, ast.Lambda):
            a = knode.args
            if len(a.args) != 1 or a.vararg or a.kwarg or a.defaults or a.kwonlyargs or a.posonlyargs:
                raise Unsupported("key= : une lambda à un seul paramètre est attendue", knode)
            pname, body_node = a.args[0].arg, knode.body
        else:  # key=len / key=str.lower / key=ma_fonction -> appel synthétique sur un paramètre
            pname = f"__k{self.tmp}"
            self.tmp += 1
            arg = ast.copy_location(ast.Name(id=pname, ctx=ast.Load()), knode)
            if isinstance(knode, ast.Name):
                body_node = ast.copy_location(ast.Call(func=knode, args=[arg], keywords=[]), knode)
            elif isinstance(knode, ast.Attribute) and isinstance(knode.value, ast.Name) and knode.value.id == "str":
                func = ast.copy_location(ast.Attribute(value=arg, attr=knode.attr, ctx=ast.Load()), knode)
                body_node = ast.copy_location(ast.Call(func=func, args=[], keywords=[]), knode)
            else:
                raise Unsupported("key= : lambda, nom de fonction ou str.méthode attendus", knode)
        bound = []
        self.bind_local(pname, et, bound)
        try:
            body = self.expr(body_node)
        finally:
            self.unbind(bound)
        if not (is_orderable(body.type) or body.type == BOOL):
            raise Unsupported(f"la clé de tri est de type {body.type} : int, float, str, bool ou tuples de ces types attendus", knode)
        return ir.Lambda(pname, et, body)

    def iterable(self, it, node):
        if isinstance(it, ast.Attribute) and it.attr == "stdin" and self.module_of(it.value) == "sys":  # for line in sys.stdin
            return ir.Call("stdin_readlines", [], list_of(STR), "builtin"), STR
        iterable = self.unopt(self.expr(it, view_ok=True))
        if iterable.type.kind == "gen":
            return iterable, iterable.type.args[0]
        if iterable.type == STR:
            iterable = self.as_list(iterable)
        elif iterable.type.kind == "tuple":
            iterable = self.tuple_as_list(iterable, node)
        elif iterable.type.kind in ("set", "deque", "vtuple"):
            iterable = self.as_list(iterable)
        if iterable.type.kind in ("list", "dict"):
            return iterable, iterable.type.args[0]  # dict : on itère sur les clés
        raise Unsupported(f"itération sur le type {iterable.type} non supportée (list, dict, range)", node)

    def for_unpack(self, node):
        """for a, b in pairs / for k, v in d.items() : la boucle porte un tuple temporaire, dépaqueté en tête de corps."""
        iterable, elem = self.iterable(node.iter, node)
        if elem.kind != "tuple":
            raise Unsupported(f"dépaquetage dans for : les éléments sont de type {elem}, un tuple est attendu", node)
        tmp = f"__t{self.tmp}"
        self.tmp += 1
        self.scope[tmp] = elem
        self.loopvars.add(tmp)
        before = set(self.scope)
        self.depth += 1  # les variables introduites par la cible sont déclarées en tête de fonction (comme dans un bloc imbriqué)
        pre = self.unpack(node.target, ir.Var(tmp, elem), node)
        self.depth -= 1
        body = pre + self.block(node.body)
        self.loopvars.discard(tmp)
        del self.scope[tmp]
        if not self.is_module:
            for n in set(self.scope) - before:  # variables de la cible : locales à la boucle (comme les variables de boucle simples)
                del self.scope[n]
        return [ir.ForEach(tmp, iterable, elem, body)]

    def coerce_int(self, e, node):
        if e.type != INT:
            raise Unsupported(f"entier attendu, {e.type} fourni", node)
        return e

    @staticmethod
    def const_int(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) \
                and type(node.operand.value) is int:
            return -node.operand.value
        return None

    def literal_int(self, node):
        v = self.const_int(node)
        if v is None:
            raise Unsupported("le pas de range() doit être une constante entière", node)
        return v

    # ---------- expressions ----------
    VIEWS = ("keys", "values", "items")

    def expr(self, node, expected=None, view_ok=False):
        m = getattr(self, "e_" + type(node).__name__, None)
        if m is None:
            hint = ""
            if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                hint = " (utilisez une boucle for)"
            elif isinstance(node, ast.Lambda):
                hint = " (utilisez une fonction)"
            raise Unsupported(f"expression non supportée : {type(node).__name__}{hint}", node)
        e = m(node, expected) if m.__code__.co_argcount == 3 else m(node)
        if not view_ok and isinstance(e, ir.MethodCall) and e.name in self.VIEWS:
            raise Unsupported(f".{e.name}() est une vue en Python (print afficherait dict_{e.name}([...])) : utilisez-la dans un for, "
                              f"avec len/sum/sorted/in, ou convertissez avec list(d.{e.name}())", node)
        if not view_ok and isinstance(e, ir.Call) and e.name in ("enumerate", "zip", "reversed", "zip_star", "range_list"):
            raise Unsupported(f"{e.name}() renvoie un itérateur en Python (print afficherait <{e.name} object ...>) : utilisez-le dans "
                              f"un for ou une compréhension, ou convertissez avec list({e.name}(...))", node)
        return e

    def e_Constant(self, node):
        v = node.value
        if isinstance(v, bool):
            return ir.Const(v, BOOL)
        if isinstance(v, int):
            if not -INT64 <= v < INT64:
                raise Unsupported("entier hors de l'intervalle 64 bits (les int Python sont non bornés)", node)
            return ir.Const(v, INT)
        if isinstance(v, float):
            return ir.Const(v, FLOAT)
        if isinstance(v, str):
            return ir.Const(v, STR)
        if v is None:
            return ir.Const(None, NONE)
        raise Unsupported(f"constante non supportée : {v!r}", node)

    def outer_var(self, name):
        p = self.parent
        while p is not None:
            if name in p.scope:
                return p.scope[name]
            p = p.parent
        return None

    def find_local_func(self, name):
        c = self
        while c is not None:
            if name in c.local_funcs:
                return c.local_funcs[name]
            c = c.parent
        return None

    def s_FunctionDef(self, node):
        if self.is_module:
            raise Unsupported("fonction définie dans un bloc de code de niveau module (if/for...) : définissez-la au premier niveau", node)
        if node.decorator_list:
            raise Unsupported("décorateur sur une fonction imbriquée non supporté", node)
        if node.returns is None:
            raise Unsupported(f"annotation de retour manquante pour {node.name}() (écrire -> None si rien)", node)
        if node.name in self.scope or node.name in self.local_funcs or node.name in self.fe.sigs or node.name in self.fe.classes:
            raise Unsupported(f"nom {node.name} déjà utilisé", node)
        params, defaults = self.fe.params_and_defaults(node)
        ret = self.fe.ret_type(node)
        if ret.kind == "gen":
            raise Unsupported("fonction génératrice imbriquée non supportée (définissez-la au premier niveau)", node)
        self.local_funcs[node.name] = (params, ret, defaults)  # avant le corps : la fonction peut s'appeler elle-même
        child = FuncConv(self.fe, node.name, params, ret, cls=self.cls, parent=self)
        lf = ir.LocalFunc(None)
        self.local_irs[node.name] = lf
        lf.func = child.run(node.body)
        lf.recursive = child.calls_self
        return [lf]

    def s_Nonlocal(self, node):
        for n in node.names:
            if self.outer_var(n) is None:
                raise Unsupported(f"`nonlocal {n}` : variable introuvable dans la fonction englobante", node)
            self.nonlocal_names.add(n)
        return []

    def e_Lambda(self, node, expected=None):
        if expected is None or expected.kind != "func":
            raise Unsupported("lambda : son type ne peut pas être déduit ; annotez la cible (f: Callable[[int], int] = lambda x: ...) "
                              "ou passez-la à une fonction dont le paramètre est annoté Callable[...]", node)
        ret, *ptypes = expected.args
        a = node.args
        if len(a.args) != len(ptypes) or a.vararg or a.kwarg or a.kwonlyargs or a.defaults or a.posonlyargs:
            raise Unsupported(f"lambda : {len(ptypes)} paramètre(s) simple(s) attendu(s) ({expected})", node)
        bound = []
        for arg, pt in zip(a.args, ptypes):
            self.bind_local(arg.arg, pt, bound)
        try:
            body = self.scoped(lambda: self.expr(node.body, ret))
        finally:
            self.unbind(bound)
        if ret != NONE:
            body = self.coerce(body, ret, node)
        return ir.LambdaVal([(arg.arg, pt) for arg, pt in zip(a.args, ptypes)], body, expected)

    def e_Name(self, node, expected=None):
        if node.id == "self" and self.in_init:
            raise Unsupported("dans __init__, `self` ne peut servir que pour accéder à un champ ou une méthode (self.x) : "
                              "l'objet n'est pas encore partageable (le passer en valeur n'est pas supporté)", node)
        if node.id in self.scope:
            t = self.fe.resolve(self.scope[node.id])
            c = self.casts.get(node.id)
            inner = t.args[0] if t.kind == "optional" else t
            if c is not None and inner.kind == "class" and c != inner:
                return ir.Downcast(ir.Unwrap(ir.Var(node.id, t), inner) if t.kind == "optional" else ir.Var(node.id, t), c)
            if node.id in self.narrowed and t.kind == "optional":
                return ir.Unwrap(ir.Var(node.id, t), t.args[0])
            return ir.Var(node.id, t)
        ov = self.outer_var(node.id)
        if ov is not None:
            return ir.Var(node.id, self.fe.resolve(ov))
        if node.id in self.fe.globals:
            return ir.Var(node.id, self.fe.resolve(self.fe.globals[node.id]))
        if node.id in self.fe.pre_globals:
            return ir.Var(node.id, self.fe.resolve(self.fe.pre_globals[node.id]))
        if node.id in self.fe.from_imports:
            return self.lib_const(self.fe.from_imports[node.id], node)
        lf = self.find_local_func(node.id)
        if lf is not None:
            c = self
            while c is not None:  # la fonction sert de valeur : elle peut survivre à la fonction englobante
                if node.id in c.local_irs:
                    c.local_irs[node.id].escapes = True
                    if c.local_irs[node.id].recursive:
                        raise Unsupported(f"fonction imbriquée récursive '{node.id}' utilisée comme valeur : non supporté", node)
                c = c.parent
            return ir.FuncRef(node.id, "local", func_of([t for _, t in lf[0]], lf[1]))
        if node.id in self.fe.sigs:
            params, ret = self.fe.sigs[node.id]
            return ir.FuncRef(node.id, "user", func_of([t for _, t in params], ret))
        if node.id in self.fe.classes and self.fe.classes[node.id].enum_members:  # for c in Couleur / list(Couleur) / len(Couleur)
            ct = class_of(node.id)
            return ir.ListLit([ir.Var(g, ct) for _, g in self.fe.classes[node.id].enum_members], list_of(ct))
        if node.id in self.fe.classes:
            raise Unsupported(f"la classe '{node.id}' ne peut pas être utilisée comme valeur", node)
        if expected is not None and expected.kind == "func" and getattr(self, "b_" + node.id, None) is not None:
            # fonction intégrée utilisée comme valeur (reduce(max, xs), map(str, xs)) : enveloppée dans une lambda
            ps = [f"__p{i}" for i in range(len(expected.args) - 1)]
            lam = ast.parse(f"lambda {', '.join(ps)}: {node.id}({', '.join(ps)})", mode="eval").body
            return self.e_Lambda(ast.copy_location(lam, node), expected)
        raise Unsupported(f"variable '{node.id}' inconnue ici (utilisée avant affectation, ou variable de boucle "
                          "utilisée après la boucle)", node)

    def obj_expr(self, node):
        """Expression servant de base à un accès `.champ` / `.méthode()` : `self` est autorisé même dans __init__."""
        if isinstance(node, ast.Name) and node.id == "self" and self.cls is not None:
            return ir.Var("self", class_of(self.cls))
        return self.unopt(self.expr(node))

    def lib_const(self, q, node):
        if q in STRING_CONSTS:
            return ir.Const(STRING_CONSTS[q], STR)
        if q in CONSTS:
            return ir.LibConst(q, CONSTS[q][0])
        raise Unsupported(f"{q} non supporté", node)

    def module_of(self, node):
        """Nom du module si `node` est un identifiant de module importé (math, string...), sinon None."""
        if isinstance(node, ast.Name) and node.id in self.fe.modules and node.id not in self.scope:
            return self.fe.modules[node.id]
        return None

    def type_name_of(self, node):
        """`type(x).__name__` / `x.__class__.__name__` : nom de la classe réelle (dynamique pour les objets d'une hiérarchie)."""
        v = node.value
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "type" and len(v.args) == 1 and not v.keywords:
            x = self.unopt(self.expr(v.args[0]))
        elif isinstance(v, ast.Attribute) and v.attr == "__class__":
            x = self.unopt(self.expr(v.value))
        else:
            return None
        if x.type.kind == "class":
            return ir.Call("type_name", [x], STR, "builtin")
        names = {"int": "int", "float": "float", "bool": "bool", "str": "str", "list": "list", "dict": "dict", "tuple": "tuple",
                 "set": "set", "deque": "deque"}
        if x.type.kind in names or x.type in (INT, FLOAT, BOOL, STR):
            return ir.Const(names[x.type.kind], STR)
        raise Unsupported(f"type(x).__name__ : type {x.type} non supporté", node)

    def e_Attribute(self, node):
        if node.attr == "__name__":
            r = self.type_name_of(node)
            if r is not None:
                return r
        if isinstance(node.value, ast.Name) and node.value.id in self.fe.classes and node.value.id not in self.scope:
            g = self.fe.lookup_classvar(node.value.id, node.attr)
            if g is None:
                raise Unsupported(f"{node.value.id}.{node.attr} : variable de classe inconnue", node)
            return self.e_Name(ast.copy_location(ast.Name(id=g, ctx=ast.Load()), node))
        mod = self.module_of(node.value)
        if mod is not None:
            return self.lib_const(f"{mod}.{node.attr}", node)
        base = self.obj_expr(node.value)
        if base.type.kind != "class":
            raise Unsupported(f"accès à .{node.attr} sur le type {base.type} non supporté", node)
        info = self.fe.classes[base.type.args[0]]
        found = self.fe.lookup_field(info.name, node.attr)
        if found is not None:
            return ir.Attr(base, node.attr, found[1][0])
        prop = self.fe.lookup_prop(info.name, node.attr)
        if prop is not None:
            return ir.UserMethodCall(base, info.name, node.attr, [], prop)
        g = self.fe.lookup_classvar(info.name, node.attr)
        if g is not None:
            return self.e_Name(ast.copy_location(ast.Name(id=g, ctx=ast.Load()), node))
        if self.fe.lookup_method(info.name, node.attr) is not None:
            raise Unsupported(f"méthode {info.name}.{node.attr} utilisée comme valeur : appelez-la ({node.attr}(...))", node)
        raise Unsupported(f"champ inconnu .{node.attr} sur {info.name} (déclarez-le dans le corps de la classe ou par self.{node.attr} = ... "
                          "dans __init__, avant de l'utiliser)", node)

    def e_UnaryOp(self, node):
        if isinstance(node.op, ast.Not):
            return ir.Unary("not", self.cond(node.operand), BOOL)
        x = self.unopt(self.expr(node.operand))
        if x.type.kind == "class" and isinstance(node.op, ast.USub):
            f = self.fe.lookup_method(x.type.args[0], "__neg__")
            if f is None:
                raise Unsupported(f"opérateur - unaire non défini pour {x.type} (définissez __neg__)", node)
            return ir.UserMethodCall(x, x.type.args[0], "__neg__", [], f[1][1])
        if isinstance(node.op, ast.Invert):
            if x.type != INT:
                raise Unsupported("~ attend un entier", node)
            return ir.Unary("~", x, INT)
        if not is_numeric(x.type):
            raise Unsupported(f"opérateur unaire sur le type {x.type}", node)
        return ir.Unary("-" if isinstance(node.op, ast.USub) else "+", x, x.type)

    def e_BinOp(self, node):
        op = BINOPS.get(type(node.op))
        if op is None:
            raise Unsupported(f"opérateur non supporté : {type(node.op).__name__}", node)
        left = self.expr(node.left)
        if op == "%" and left.type == STR:
            return self.percent_format(node, left, node.right)
        return self.binop(op, left, self.expr(node.right), node)

    def binop(self, op, l, r, node):
        l, r = self.unopt(l), self.unopt(r)
        lt, rt = l.type, r.type
        if lt.kind == "class":
            dn = {"+": "__add__", "-": "__sub__", "*": "__mul__", "/": "__truediv__", "//": "__floordiv__", "%": "__mod__"}.get(op)
            f = self.fe.lookup_method(lt.args[0], dn) if dn else None
            if f is None:
                raise Unsupported(f"opérateur {op} non défini pour {lt} (définissez {dn or 'la méthode spéciale'})", node)
            params, ret, _ = f[1]
            return ir.UserMethodCall(l, lt.args[0], dn, [self.coerce(r, params[0][1], node)], ret)
        if op == "+" and lt == STR and rt == STR:
            return ir.BinOp("+", l, r, STR)
        if op == "+" and lt.kind == "list" and rt.kind == "list" and self.fe.unify(lt, rt):
            return ir.BinOp("+", l, r, self.fe.resolve(lt))  # nouvelle liste
        if op == "*" and ((lt.kind == "list" or lt == STR) and rt == INT):
            if lt.kind == "list":
                self.value_elems(lt, "répéter", node)
            return ir.BinOp("*", l, r, lt)
        if op == "*" and lt == INT and (rt.kind == "list" or rt == STR):
            if rt.kind == "list":
                self.value_elems(rt, "répéter", node)
            return ir.BinOp("*", r, l, rt)
        if lt.kind == "dict" and rt.kind == "dict" and op == "|" and self.fe.unify(lt, rt):
            return ir.Call("dict_merge", [l, r], self.fe.resolve(lt), "builtin")
        if lt.kind == "set" and rt.kind == "set" and op in ("|", "&", "-", "^") and self.fe.unify(lt, rt):
            name = {"|": "set_union", "&": "set_inter", "-": "set_diff", "^": "set_symdiff"}[op]
            return ir.Call(name, [l, r], self.fe.resolve(lt), "builtin")
        if not (is_numeric(lt) and is_numeric(rt)):
            raise Unsupported(f"opérateur {op} non supporté entre {lt} et {rt}", node)
        if op == "/":
            return ir.BinOp("/i" if lt == INT and rt == INT else "/", self.promote(l), self.promote(r), FLOAT)
        if op in ("//", "%", "&", "|", "^", "<<", ">>"):
            if lt != INT or rt != INT:
                raise Unsupported(f"opérateur {op} supporté uniquement entre entiers (pas de {lt}/{rt})", node)
            return ir.BinOp(op, l, r, INT)
        if op == "**":
            if lt == INT and rt == INT:
                if isinstance(r, ir.Const) and r.value < 0:
                    raise Unsupported("exposant entier négatif (le résultat Python est un float)", node)
                return ir.BinOp("**", l, r, INT)
            return ir.BinOp("**", self.promote(l), self.promote(r), FLOAT)
        if lt == INT and rt == INT:
            return ir.BinOp(op, l, r, INT)
        return ir.BinOp(op, self.promote(l), self.promote(r), FLOAT)

    def value_elems(self, t, verb, node):
        """Plus de restriction : [[0]] * 3 partage la sous-liste comme en Python (les poignées sont copiées, pas les listes)."""
        return None

    def e_BoolOp(self, node):
        op = "and" if isinstance(node.op, ast.And) else "or"
        vals = self.bool_operands(node, self.expr)
        if any(v.type != BOOL for v in vals):
            # `a or b` / `a and b` renvoient un OPÉRANDE en Python : réécrit en `a if truthy(a) else b` (a ne doit pas avoir d'effet de bord)
            t = vals[0].type
            if any(v.type != t for v in vals) or not all(self.is_pure(v) for v in vals[:-1]):
                raise Unsupported("and/or sur des valeurs non booléennes : opérandes de même type et sans effet de bord attendus "
                                  "(le résultat Python est un opérande, pas un bool)", node)
            out = vals[-1]
            for v in reversed(vals[:-1]):
                out = ir.Ternary(self.truthy(v), v, out, t) if op == "or" else ir.Ternary(self.truthy(v), out, v, t)
            return out
        return ir.BoolOp(op, vals)

    def e_Compare(self, node):
        exprs = [self.expr(node.left)]
        parts = []
        for op, rn in zip(node.ops, node.comparators):
            right = self.expr(rn, view_ok=isinstance(op, (ast.In, ast.NotIn)))
            if isinstance(op, (ast.In, ast.NotIn)) and right.type.kind == "tuple":
                right = self.tuple_as_list(right, node)
            parts.append(self.cmp1(op, exprs[-1], right, node))
            exprs.append(right)
        if len(parts) > 1 and any(not self.is_pure(e) for e in exprs[1:-1]):
            raise Unsupported("comparaison chaînée dont un opérande intermédiaire a des effets de bord (appel de fonction) : "
                              "écrivez deux comparaisons avec `and`", node)
        return parts[0] if len(parts) == 1 else ir.BoolOp("and", parts)

    def cmp1(self, op, l, r, node):
        sym = CMPOPS.get(type(op))
        if sym is None:
            raise Unsupported(f"comparaison non supportée : {type(op).__name__}", node)
        if sym in ("is", "isnot"):
            if l.type == NONE or r.type == NONE:
                other = r if l.type == NONE else l
                if other.type == NONE:
                    return ir.Const(sym == "is", BOOL)
                if other.type.kind != "optional":  # une valeur jamais None : `x is None` est toujours faux
                    if not self.is_pure(other):
                        raise Unsupported("`is None` sur une expression non simple dont le type n'est pas Optional", node)
                    return ir.Const(sym == "isnot", BOOL)
                return ir.IsNone(other, sym == "isnot")
            lo, ro = self.fe.resolve(l.type), self.fe.resolve(r.type)
            if lo.kind in ("class", "optional") and ro.kind in ("class", "optional"):
                return ir.Cmp(sym, l, r)  # identité d'objets
            raise Unsupported("`is` : seulement `x is None` et l'identité de deux objets", node)
        if sym in ("==", "!=") and (l.type.kind == "optional" or r.type.kind == "optional" or l.type == NONE or r.type == NONE):
            if l.type == NONE and r.type == NONE:
                return ir.Const(sym == "==", BOOL)
            base = r.type if l.type == NONE else l.type
            target = optional_of(base)
            return ir.Cmp(sym, self.coerce(l, target, node), self.coerce(r, target, node))
        if l.type.kind == "class" and sym in ("==", "!="):
            f = self.fe.lookup_method(l.type.args[0], "__eq__")
            if f is not None:
                call = ir.UserMethodCall(l, l.type.args[0], "__eq__", [self.coerce(r, f[1][0][0][1], node)], BOOL)
                return call if sym == "==" else ir.Unary("not", call, BOOL)
        if l.type.kind == "class" and sym in ("<", "<=", ">", ">="):
            direct = {"<": "__lt__", "<=": "__le__", ">": "__gt__", ">=": "__ge__"}[sym]
            reflected = {"<": "__gt__", "<=": "__ge__", ">": "__lt__", ">=": "__le__"}[sym]
            f = self.fe.lookup_method(l.type.args[0], direct)
            if f is not None:
                return ir.UserMethodCall(l, l.type.args[0], direct, [self.coerce(r, f[1][0][0][1], node)], BOOL)
            if r.type.kind == "class":
                f = self.fe.lookup_method(r.type.args[0], reflected)
                if f is not None:
                    return ir.UserMethodCall(r, r.type.args[0], reflected, [self.coerce(l, f[1][0][0][1], node)], BOOL)
            raise Unsupported(f"comparaison {sym} non définie pour {l.type} (définissez {direct})", node)
        if sym in ("in", "notin") and r.type.kind == "class":
            f = self.fe.lookup_method(r.type.args[0], "__contains__")
            if f is None:
                raise Unsupported(f"`in` non défini pour {r.type} (définissez __contains__)", node)
            call = ir.UserMethodCall(r, r.type.args[0], "__contains__", [self.coerce(l, f[1][0][0][1], node)], BOOL)
            return call if sym == "in" else ir.Unary("not", call, BOOL)
        if sym not in ("==", "!=", "in", "notin"):
            l, r = self.unopt(l), self.unopt(r)
        if sym in ("in", "notin"):
            r = self.unopt(r)
        if sym in ("in", "notin"):
            ok = ((r.type.kind in ("list", "set", "deque", "vtuple") and l.type == r.type.args[0]) or (r.type.kind == "dict" and l.type == r.type.args[0])
                  or (r.type == STR and l.type == STR))
            if not ok:
                raise Unsupported(f"`{'not ' if sym == 'notin' else ''}in` non supporté entre {l.type} et {r.type}", node)
            return ir.Cmp(sym, l, r)
        if is_numeric(l.type) and is_numeric(r.type) and l.type != r.type:
            l, r = self.promote(l), self.promote(r)
        if l.type != r.type and not self.fe.unify(l.type, r.type):
            raise Unsupported(f"comparaison entre types différents : {l.type} {sym} {r.type}", node)
        if l.type.kind == "set" and sym in ("<", "<=", ">", ">="):
            a, b = (l, r) if sym in ("<", "<=") else (r, l)
            return ir.Call("set_lt" if sym in ("<", ">") else "set_issubset", [a, b], BOOL, "builtin")
        if sym not in ("==", "!=") and not is_orderable(l.type):
            raise Unsupported(f"comparaison d'ordre {sym} non supportée pour le type {l.type}", node)
        return ir.Cmp(sym, l, r)

    def e_IfExp(self, node, expected=None):
        c = self.cond(node.test)
        a = self.scoped(lambda: self.expr(node.body, expected), self.narrow_set(node.test, True), self.cast_set(node.test, True))
        b = self.scoped(lambda: self.expr(node.orelse, expected), self.narrow_set(node.test, False), self.cast_set(node.test, False))
        if a.type != b.type and (a.type == NONE or b.type == NONE or a.type.kind == "optional" or b.type.kind == "optional"):
            base = b.type if a.type == NONE else a.type
            t = optional_of(base)
            a, b = self.coerce(a, t, node), self.coerce(b, t, node)
        if a.type != b.type and a.type.kind == "class" and b.type.kind == "class":
            lub = self.fe.lub_class([a.type.args[0], b.type.args[0]])
            if lub is not None:
                a, b = self.coerce(a, class_of(lub), node), self.coerce(b, class_of(lub), node)
                return ir.Ternary(c, a, b, class_of(lub))
        if a.type != b.type:
            raise Unsupported(f"les deux branches de l'expression conditionnelle ont des types différents ({a.type}, {b.type}) : "
                              "en Python le type du résultat dépendrait de la valeur de la condition", node)
        return ir.Ternary(c, a, b, a.type)

    def e_JoinedStr(self, node):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(ir.Const(v.value, STR))
            elif isinstance(v, ast.FormattedValue):
                spec = self.e_JoinedStr(v.format_spec) if v.format_spec is not None else ir.Const("", STR)
                conv = {-1: None, 115: "s", 114: "r", 97: "a"}[v.conversion]
                parts.append(self.format_part(self.expr(v.value), spec, conv, node))
        return self.concat(parts)

    def e_Tuple(self, node, expected=None):
        if not node.elts:
            raise Unsupported("tuple vide () non supporté", node)
        if any(isinstance(e, ast.Starred) for e in node.elts):
            raise Unsupported("tuple avec *étoile non supporté", node)
        exp = expected.args if expected is not None and expected.kind == "tuple" and len(expected.args) == len(node.elts) \
            else [None] * len(node.elts)
        elems = [self.expr(e, t) for e, t in zip(node.elts, exp)]
        for e in elems:
            if not is_value_type(e.type):
                raise Unsupported(f"élément de tuple de type {e.type} non supporté (seulement int, float, bool, str et tuples : "
                                  "en Python un tuple contenant une liste partage sa référence)", node)
        return ir.TupleLit(elems, tuple_of(*[e.type for e in elems]))

    def empty_hint(self, node, tag):
        """Type d'un élément/clé/valeur d'un littéral vide, déduit de l'usage (indice de la passe à blanc)."""
        token = (node.lineno, node.col_offset, tag)
        h = self.fe.hints.get(token)
        if h is not None:
            return self.fe.resolve(h)
        if self.fe.dry:
            return pending(token)
        raise Unsupported("conteneur vide dont le type n'a pas pu être déduit de son usage (aucun append/affectation/retour/argument "
                          "typé trouvé) : annotez la variable, par ex. `xs: list[int] = []`", node)

    def e_List(self, node, expected=None):
        if any(isinstance(e, ast.Starred) for e in node.elts):  # [*a, x, *b] : concaténation de morceaux
            pieces, cur = [], []
            for e in node.elts:
                if isinstance(e, ast.Starred):
                    if cur:
                        pieces.append(self.e_List(ast.copy_location(ast.List(elts=cur, ctx=ast.Load()), node), expected))
                        cur = []
                    pieces.append(self.seq(e.value))
                else:
                    cur.append(e)
            if cur:
                pieces.append(self.e_List(ast.copy_location(ast.List(elts=cur, ctx=ast.Load()), node), expected))
            out = pieces[0]
            for nxt in pieces[1:]:
                if not self.fe.unify(out.type, nxt.type):
                    raise Unsupported(f"[*...] : éléments de types différents ({out.type}, {nxt.type})", node)
                out = ir.BinOp("+", out, nxt, self.fe.resolve(out.type))
            return ir.Call("list", [out], out.type, "builtin") if len(pieces) == 1 else out
        et = expected.args[0] if expected is not None and expected.kind == "list" else None
        elems = [self.fresh(self.expr(e, et), node) for e in node.elts]
        if et is None:
            if not elems:
                et = self.empty_hint(node, "elem")
            else:
                real = [e.type for e in elems if e.type != NONE]
                et = real[0] if real else self.empty_hint(node, "elem")
                if len(set(real)) > 1 and all(t.kind == "class" for t in real):  # [Cercle(), Carre()] : liste de leur ancêtre commun
                    lub = self.fe.lub_class([t.args[0] for t in real])
                    if lub is not None:
                        et = class_of(lub)
                if len(real) != len(elems):  # [1, None, 3] : liste d'Optional[int]
                    et = optional_of(et)
        elems = [self.coerce(e, et, node) for e in elems]
        return ir.ListLit(elems, list_of(et))

    def e_Dict(self, node, expected=None):
        if any(k is None for k in node.keys):  # {**a, 'x': 1, **b} : fusions successives
            pieces, ks, vs = [], [], []
            for k, v in zip(node.keys, node.values):
                if k is None:
                    if ks:
                        pieces.append(self.e_Dict(ast.copy_location(ast.Dict(keys=ks, values=vs), node), expected))
                        ks, vs = [], []
                    pieces.append(self.unopt(self.expr(v, expected)))
                else:
                    ks.append(k)
                    vs.append(v)
            if ks:
                pieces.append(self.e_Dict(ast.copy_location(ast.Dict(keys=ks, values=vs), node), expected))
            out = pieces[0]
            for nxt in pieces[1:]:
                if out.type.kind != "dict" or not self.fe.unify(out.type, nxt.type):
                    raise Unsupported(f"{{**...}} : dict de types différents ({out.type}, {nxt.type})", node)
                out = ir.Call("dict_merge", [out, nxt], self.fe.resolve(out.type), "builtin")
            return ir.Call("dict_plain", [out], out.type, "builtin") if len(pieces) == 1 else out
        kt, vt = (expected.args if expected is not None and expected.kind == "dict" else (None, None))
        if kt is None:
            if not node.keys:
                kt, vt = self.empty_hint(node, "k"), self.empty_hint(node, "v")
            else:
                kt = self.expr(node.keys[0]).type
                vt = self.expr(node.values[0]).type
        keys = [self.coerce(self.expr(k, kt), kt, node) for k in node.keys]
        vals = [self.coerce(self.fresh(self.expr(v, vt), node), vt, node) for v in node.values]
        return ir.DictLit(keys, vals, dict_of(kt, vt))

    def e_Subscript(self, node):
        return self.index(node)

    def index(self, node):
        base = self.unopt(self.expr(node.value, view_ok=True))
        if isinstance(node.slice, ast.Slice):
            return self.slice_expr(node, base)
        t = base.type
        if t.kind == "tuple":
            i = self.const_int(node.slice)
            if i is None:
                raise Unsupported("l'indice d'un tuple doit être une constante entière (le type du résultat en dépend)", node)
            n = len(t.args)
            if not -n <= i < n:
                raise Unsupported(f"indice {i} hors d'un tuple de {n} éléments", node)
            i %= n
            return ir.TupleGet(base, i, t.args[i])
        if t.kind == "class":
            f = self.fe.lookup_method(t.args[0], "__getitem__")
            if f is None:
                raise Unsupported(f"indexation non définie pour {t} (définissez __getitem__)", node)
            params, ret, _ = f[1]
            return ir.UserMethodCall(base, t.args[0], "__getitem__", [self.coerce(self.expr(node.slice, params[0][1]), params[0][1], node)], ret)
        if t.kind in ("list", "deque", "vtuple"):
            return ir.Index(base, self.coerce_int(self.expr(node.slice), node), t.args[0])
        if t == STR:
            return ir.Index(base, self.coerce_int(self.expr(node.slice), node), STR)
        if t.kind == "dict":
            k = self.coerce(self.expr(node.slice, t.args[0]), t.args[0], node)
            return ir.Index(base, k, t.args[1])
        raise Unsupported(f"indexation non supportée sur le type {t}", node)

    # ---------- appels ----------
    def num_arg(self, a, node):
        if not is_numeric(a.type):
            raise Unsupported(f"argument numérique attendu, {a.type} fourni", node)
        return self.promote(a)

    def lib_call(self, q, node):
        if node.keywords:
            raise Unsupported(f"{q}() : arguments nommés non supportés", node)
        args = [self.expr(a) for a in node.args]
        if q == "math.prod":
            if len(args) != 1:
                raise Unsupported("math.prod(liste)", node)
            xs = self.as_list(self.unopt(args[0]), True)
            if xs.type.kind != "list" or not is_numeric(xs.type.args[0]):
                raise Unsupported(f"math.prod() attend une liste de nombres, pas {xs.type}", node)
            return ir.Call("prod", [xs], xs.type.args[0], "builtin")
        if q == "math.log":
            if len(args) not in (1, 2):
                raise Unsupported("math.log() attend 1 ou 2 arguments", node)
            return ir.Call(q, [self.num_arg(a, node) for a in args], FLOAT, "lib")
        fn = LIB.get(q)
        if fn is None:
            raise Unsupported(f"{q}() non supporté", node)
        if len(args) != len(fn.args):
            raise Unsupported(f"{q}() attend {len(fn.args)} argument(s)", node)
        conv = []
        for a, kind in zip(args, fn.args):
            conv.append(self.num_arg(a, node) if kind == "num" else self.coerce_int(a, node) if kind == "int" else self.coerce(a, STR, node))
        return ir.Call(q, conv, fn.ret, "lib")

    GEN_FUNCS = {"sum", "min", "max", "any", "all", "sorted", "list", "set", "tuple", "deque", "Counter", "frozenset"}

    def e_Call(self, node, expected=None):
        f = node.func
        fname = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
        if fname in self.GEN_FUNCS:
            self.allowed_gens.update(a for a in node.args if isinstance(a, ast.GeneratorExp))
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute) and self.module_of(f.value.value) == "sys" \
                and f.value.attr in ("stdin", "stdout", "stderr"):
            return self.stdio_call(node, f.value.attr, f.attr)
        if isinstance(f, ast.Attribute) and f.attr == "from_iterable" and (
                (isinstance(f.value, ast.Attribute) and f.value.attr == "chain" and self.module_of(f.value.value) == "itertools")
                or (isinstance(f.value, ast.Name) and f.value.id not in self.scope and self.fe.from_imports.get(f.value.id) == "itertools.chain")):
            return self.c_chain_from_iterable(node, expected)
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "dict" and f.attr == "fromkeys" \
                and "dict" not in self.scope:
            return self.dict_fromkeys(node)
        mod = self.module_of(f.value) if isinstance(f, ast.Attribute) else None
        if mod in COLL_MODULES:
            if f.attr not in COLL_NAMES[mod]:
                raise Unsupported(f"{mod}.{f.attr}() non supporté", node)
            return self.coll_call(f.attr, node, expected)
        if mod is not None:
            return self.lib_call(f"{mod}.{f.attr}", node)
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in self.fe.classes and f.value.id not in self.scope:
            st = self.fe.lookup_static(f.value.id, f.attr)
            if st is None:
                raise Unsupported(f"{f.value.id}.{f.attr}() : seules les méthodes @staticmethod / @classmethod s'appellent sur la classe", node)
            if st[1] and st[2] != f.value.id:
                raise Unsupported(f"méthode de classe {st[2]}.{f.attr} appelée via la sous-classe {f.value.id} : non supporté", node)
            return self.user_call(st[0], node)
        if isinstance(f, ast.Attribute):
            return self.method_call(node)
        if isinstance(f, (ast.Subscript, ast.Call)):  # ops["+"](1, 2) / make_adder(3)(4)
            return self.call_value(self.expr(f), node)
        if not isinstance(f, ast.Name):
            raise Unsupported("appel non supporté", node)
        n = f.id
        vt = self.scope.get(n) if n in self.scope else (self.outer_var(n) or self.fe.globals.get(n))
        if vt is not None and self.fe.resolve(vt).kind == "func":
            return self.call_value(self.e_Name(f), node)
        if vt is not None and self.fe.resolve(vt).kind == "class" and self.fe.lookup_method(self.fe.resolve(vt).args[0], "__call__"):
            obj = self.e_Name(f)  # instance appelable : obj(args) -> obj.__call__(args)
            owner, (params, ret, defaults) = self.fe.lookup_method(obj.type.args[0], "__call__")
            return ir.UserMethodCall(obj, obj.type.args[0], "__call__", self.bind_args(node, params, defaults, f"{n}()", callee=f"{owner.name}.__call__"), ret)
        lf = self.find_local_func(n) if n not in self.scope else None
        if lf is not None:
            params, ret, defaults = lf
            if n == self.name and self.parent is not None:
                self.calls_self = True
            return ir.Call(n, self.bind_args(node, params, defaults, f"{n}()"), ret, "local")
        if n in self.fe.sigs:
            return self.user_call(n, node)
        if n in self.fe.classes:
            return self.construct(n, node)
        if n in self.fe.from_imports and n not in self.scope:
            q = self.fe.from_imports[n]
            if q.split(".")[0] in COLL_MODULES:
                return self.coll_call(q.split(".", 1)[1], node, expected)
            return self.lib_call(q, node)
        if n == "set" and n not in self.scope:
            return self.c_set(node, expected)
        handler = getattr(self, "b_" + n, None)
        if handler is None:
            raise Unsupported(f"fonction inconnue ou non supportée : {n}()", node)
        if node.keywords and n not in ("sorted", "min", "max"):
            raise Unsupported(f"{n}() : arguments nommés non supportés pour les fonctions intégrées", node)
        if n in ("sum", "min", "max", "any", "all", "sorted", "list"):
            self.allowed_gens.update(a for a in node.args if isinstance(a, ast.GeneratorExp))
        return handler(node)

    def bind_args(self, node, params, defaults, label, callee=None):
        """Lie arguments positionnels et nommés aux paramètres, complète avec les défauts, vérifie les types (stricts)."""
        n = len(params)
        vararg = defaults.get("__vararg__", False)
        npos = n - 1 if vararg else n  # paramètres positionnels ordinaires (le dernier est *args le cas échéant)
        if len(node.args) > npos and not vararg:
            raise Unsupported(f"{label} attend au plus {n} argument(s), {len(node.args)} fourni(s)", node)
        bound = [None] * n
        packed = None
        for i, a in enumerate(node.args):
            if isinstance(a, ast.Starred):
                if not vararg or i != len(node.args) - 1 or i < npos:
                    raise Unsupported("*liste dans un appel : seulement en dernier argument, vers un paramètre *args", node)
                packed = a.value
            elif i < npos:
                bound[i] = a
        extra = [a for a in node.args[npos:] if not isinstance(a, ast.Starred)] if vararg else []
        names = [p for p, _ in params]
        for kw in node.keywords:
            if kw.arg is None:
                raise Unsupported("**kwargs dans un appel non supporté", node)
            if kw.arg not in names:
                raise Unsupported(f"{label} : paramètre inconnu '{kw.arg}'", node)
            i = names.index(kw.arg)
            if bound[i] is not None:
                raise Unsupported(f"{label} : paramètre '{kw.arg}' fourni deux fois", node)
            bound[i] = kw.value
        out = []
        for i, ((pn, pt), a) in enumerate(zip(params, bound)):
            if vararg and i == n - 1:  # *args : arguments en trop (ou *liste) regroupés
                if packed is not None:
                    xs = self.as_list(self.unopt(self.expr(packed, view_ok=True)))
                    if xs.type.kind != "list" or not self.fe.unify(xs.type, list_of(pt.args[0])):
                        raise Unsupported(f"*{ast.unparse(packed)} : liste de {pt.args[0]} attendue", node)
                    out.append(ir.Call("list", [xs], pt, "builtin"))
                else:
                    elems = [self.coerce(self.expr(x, pt.args[0]), pt.args[0], node) for x in extra]
                    out.append(ir.ListLit(elems, pt))
                continue
            if a is None:
                if pn not in defaults:
                    raise Unsupported(f"{label} : argument '{pn}' manquant", node)
                dv = defaults[pn]
                if isinstance(dv, GlobalDefault):
                    if dv.name not in self.fe.globals:
                        raise Unsupported(f"{label} : valeur par défaut '{dv.name}' inconnue (constante de module attendue)", node)
                    dv = self.coerce(ir.Var(dv.name, self.fe.resolve(self.fe.globals[dv.name])), pt, node)
                out.append(dv)
                continue
            e = self.coerce(self.expr(a, pt), pt, node)
            out.append(e)
            if callee and is_container(pt) and isinstance(e, ir.Var) and e.name in self.pnames:
                self.callsites.append((callee, i, e.name))
        return out

    def call_value(self, fn, node):
        if fn.type.kind != "func":
            raise Unsupported(f"appel d'une valeur de type {fn.type} (une fonction est attendue)", node)
        ret, *ptypes = fn.type.args
        if len(node.args) != len(ptypes) or node.keywords:
            raise Unsupported(f"appel de fonction-valeur : {len(ptypes)} argument(s) positionnel(s) attendu(s)", node)
        args = [self.coerce(self.expr(a, pt), pt, node) for a, pt in zip(node.args, ptypes)]
        return ir.CallVal(fn, args, ret)

    def user_call(self, name, node):
        params, ret = self.fe.sigs[name]
        args = self.bind_args(node, params, self.fe.fdefaults.get(name, {}), f"{name}()", callee=name)
        return ir.Call(name, args, ret, "user")

    def construct(self, cname, node):
        info = self.fe.classes[cname]
        if info.enum_members and len(node.args) == 1 and not node.keywords:  # Couleur(2) : recherche par valeur
            fname = f"{cname}_from_value"
            params, ret = self.fe.sigs[fname]
            return ir.Call(fname, self.bind_args(node, params, {}, f"{cname}()"), ret, "user")
        eff = None if info.is_dataclass else self.fe.effective_init(cname)
        if info.is_exc and eff is None:  # exception sans __init__ : arguments libres (conservés dans .args)
            if node.keywords:
                raise Unsupported(f"{cname}() : arguments nommés non supportés", node)
            return ir.New(cname, [self.unopt(self.expr(a)) for a in node.args], class_of(cname))
        if info.is_dataclass:
            params = [(n, t) for n, (t, _) in info.fields.items()]
            defaults = {n: d for n, (_, d) in info.fields.items() if d is not None}
            callee = None
        else:
            params, _, defaults = eff[1] if eff else ([], NONE, {})
            callee = f"{eff[0].name}.__init__" if eff else None
        args = self.bind_args(node, params, defaults, f"{cname}()", callee=callee)
        return ir.New(cname, args, class_of(cname))

    def need(self, node, n, view_ok=False, keep_opt=False):
        if len(node.args) != n:
            raise Unsupported(f"{node.func.id}() attend {n} argument(s)", node)
        xs = [self.expr(a, view_ok=view_ok) for a in node.args]
        return xs if keep_opt else [self.unopt(x) for x in xs]

    def b_dict(self, node):
        if len(node.args) == 1 and not node.keywords:  # dict(d) : copie en dict ordinaire (perd le comportement Counter/defaultdict)
            x = self.unopt(self.expr(node.args[0]))
            if x.type.kind == "dict":
                return ir.Call("dict_plain", [x], x.type, "builtin")
        if node.args or node.keywords:
            raise Unsupported("dict() : seule la copie dict(d) est supportée (sinon littéral {k: v} ou compréhension)", node)
        return ir.DictLit([], [], dict_of(self.empty_hint(node, "k"), self.empty_hint(node, "v")))

    def fn_application(self, f, args, node):
        """AST de l'application `f(args...)` ; une lambda littérale est développée en place (ses paramètres remplacés par les arguments)."""
        if isinstance(f, ast.Lambda):
            a = f.args
            if len(a.args) != len(args) or a.vararg or a.kwarg or a.defaults or a.kwonlyargs:
                raise Unsupported(f"lambda à {len(args)} paramètre(s) attendue", node)
            subst = {p.arg: arg for p, arg in zip(a.args, args)}

            class Sub(ast.NodeTransformer):
                def visit_Name(self, n):
                    return subst[n.id] if n.id in subst and isinstance(n.ctx, ast.Load) else n

            return ast.copy_location(Sub().visit(ast.parse(ast.unparse(f.body), mode="eval").body), node)
        return ast.copy_location(ast.Call(func=f, args=list(args), keywords=[]), node)

    def b_map(self, node):
        if len(node.args) < 2 or node.keywords:
            raise Unsupported("map(f, itérable[, itérable]) : arguments positionnels seulement", node)
        names = [f"__m{self.tmp + i}" for i in range(len(node.args) - 1)]
        self.tmp += len(names)
        loads = [ast.copy_location(ast.Name(id=n, ctx=ast.Load()), node) for n in names]
        elt = self.fn_application(node.args[0], loads, node)
        if len(names) == 1:
            target, it = ast.copy_location(ast.Name(id=names[0], ctx=ast.Store()), node), node.args[1]
        else:
            target = ast.copy_location(ast.Tuple(elts=[ast.copy_location(ast.Name(id=n, ctx=ast.Store()), node) for n in names],
                                                 ctx=ast.Store()), node)
            it = ast.copy_location(ast.Call(func=ast.Name(id="zip", ctx=ast.Load()), args=list(node.args[1:]), keywords=[]), node)
        gen = ast.comprehension(target=target, iter=it, ifs=[], is_async=0)
        lc = ast.copy_location(ast.ListComp(elt=elt, generators=[gen]), node)
        return self.comp(lc, "list", None)

    def b_filter(self, node):
        if len(node.args) != 2 or node.keywords:
            raise Unsupported("filter(f, itérable) : arguments positionnels seulement", node)
        name = f"__m{self.tmp}"
        self.tmp += 1
        load = ast.copy_location(ast.Name(id=name, ctx=ast.Load()), node)
        f = node.args[0]
        test = load if (isinstance(f, ast.Constant) and f.value is None) else self.fn_application(f, [load], node)
        gen = ast.comprehension(target=ast.copy_location(ast.Name(id=name, ctx=ast.Store()), node), iter=node.args[1], ifs=[test], is_async=0)
        lc = ast.copy_location(ast.ListComp(elt=load, generators=[gen]), node)
        return self.comp(lc, "list", None)

    def b_next(self, node):
        if not 1 <= len(node.args) <= 2 or node.keywords:
            raise Unsupported("next(générateur[, défaut])", node)
        g = self.unopt(self.expr(node.args[0]))
        if g.type.kind != "gen":
            raise Unsupported(f"next() attend un générateur, pas {g.type}", node)
        et = g.type.args[0]
        if len(node.args) == 1:
            return ir.Call("gen_next", [g], et, "builtin")
        return ir.Call("gen_next_default", [g, self.coerce(self.expr(node.args[1], et), et, node)], et, "builtin")

    def b_tuple(self, node):
        if len(node.args) != 1 or node.keywords:
            raise Unsupported("tuple(iterable) attend un argument (tuple() vide non supporté)", node)
        x = self.as_list(self.unopt(self.expr(node.args[0], view_ok=True)))
        if x.type.kind != "list":
            raise Unsupported(f"tuple() attend une liste ou une chaîne, pas {x.type}", node)
        return ir.Call("list", [x], vtuple_of(x.type.args[0]), "builtin")

    def b_list(self, node):
        if not node.args:  # list() : liste vide, typée par l'usage comme []
            return ir.ListLit([], list_of(self.empty_hint(node, "elem")))
        (x,) = self.need(node, 1, view_ok=True)
        x = self.as_list(x)
        if x.type.kind != "list":
            raise Unsupported(f"list() attend une liste, une chaîne ou une vue de dict, pas {x.type}", node)
        return ir.Call("list", [x], x.type, "builtin")

    def b_any(self, node):
        (x,) = self.need(node, 1, view_ok=True)
        if x.type != list_of(BOOL):
            raise Unsupported(f"any() attend une liste de bool (ou une génératrice de bool), pas {x.type} : "
                              "any(x > 0 for x in xs) est supporté, any(xs) sur des int ne l'est pas", node)
        return ir.Call("any", [x], BOOL, "builtin")

    def b_all(self, node):
        (x,) = self.need(node, 1, view_ok=True)
        if x.type != list_of(BOOL):
            raise Unsupported(f"all() attend une liste de bool (ou une génératrice de bool), pas {x.type}", node)
        return ir.Call("all", [x], BOOL, "builtin")

    def b_enumerate(self, node):
        if len(node.args) not in (1, 2):
            raise Unsupported("enumerate() attend 1 ou 2 arguments", node)
        x = self.as_list(self.unopt(self.expr(node.args[0], view_ok=True)))
        if x.type.kind != "list":
            raise Unsupported(f"enumerate() attend une liste ou une chaîne, pas {x.type}", node)
        start = self.coerce_int(self.expr(node.args[1]), node) if len(node.args) == 2 else ir.Const(0, INT)
        return ir.Call("enumerate", [x, start], list_of(tuple_of(INT, x.type.args[0])), "builtin")

    def b_zip(self, node):
        if len(node.args) == 1 and isinstance(node.args[0], ast.Starred) and not node.keywords:  # zip(*m) : transposition
            m = self.unopt(self.expr(node.args[0].value))
            if m.type.kind != "list" or self.fe.resolve(m.type.args[0]).kind != "list":
                raise Unsupported(f"zip(*m) attend une liste de listes, pas {m.type}", node)
            return ir.Call("zip_star", [m], list_of(vtuple_of(self.fe.resolve(m.type.args[0]).args[0])), "builtin")
        if len(node.args) not in (2, 3):
            raise Unsupported("zip() : deux ou trois séquences sont supportées (zip(*m) ne l'est pas)", node)
        raw = [self.unopt(self.expr(x, view_ok=True)) for x in node.args]
        others = [r for r in raw if r.type.kind != "gen"]
        if others and len(others) < len(raw):  # zip(gen, liste) : le générateur est borné par la plus courte des autres séquences
            lens = [ir.Call("len", [self.as_list(r)], INT, "builtin") for r in others]
            bound = lens[0] if len(lens) == 1 else ir.Call("min", lens, INT, "builtin")
            raw = [ir.Call("gen_take", [r, bound], list_of(r.type.args[0]), "builtin") if r.type.kind == "gen" else r for r in raw]
        xs = [self.as_list(r) for r in raw]
        for x in xs:
            if x.type.kind != "list":
                raise Unsupported(f"zip() attend des listes ou des chaînes, pas {x.type}", node)
        return ir.Call("zip", xs, list_of(tuple_of(*[x.type.args[0] for x in xs])), "builtin")

    def b_reversed(self, node):
        (x,) = self.need(node, 1, view_ok=True)
        x = self.as_list(x)
        if x.type.kind != "list":
            raise Unsupported(f"reversed() attend une liste ou une chaîne, pas {x.type}", node)
        return ir.Call("reversed", [x], x.type, "builtin")

    def b_len(self, node):
        (x,) = self.need(node, 1, view_ok=True)
        if x.type.kind == "tuple" and self.is_pure(x):
            return ir.Const(len(x.type.args), INT)
        if x.type.kind == "class" and self.fe.lookup_method(x.type.args[0], "__len__") is not None:
            return ir.UserMethodCall(x, x.type.args[0], "__len__", [], INT)
        if not (x.type == STR or is_container(x.type) or x.type.kind == "vtuple"):
            raise Unsupported(f"len() non supporté sur {x.type}", node)
        return ir.Call("len", [x], INT, "builtin")

    def b_abs(self, node):
        (x,) = self.need(node, 1)
        if not is_numeric(x.type):
            raise Unsupported("abs() attend un nombre", node)
        return ir.Call("abs", [x], x.type, "builtin")

    def b_range(self, node):
        r = self.range_args(node, node)
        start, stop, step = r
        return ir.Call("range_list", [start, stop, ir.Const(step, INT) if isinstance(step, int) else step], list_of(INT), "builtin")

    def b_int(self, node):
        if len(node.args) == 2 and not node.keywords:
            s = self.coerce(self.expr(node.args[0]), STR, node)
            base = self.coerce_int(self.expr(node.args[1]), node)
            return ir.Call("int_base", [s, base], INT, "builtin")
        (x,) = self.need(node, 1)
        if x.type == STR:
            return ir.Call("int_str", [x], INT, "builtin")
        if x.type == INT:
            return x
        if x.type in (FLOAT, BOOL):
            return ir.Cast(x, INT)
        raise Unsupported(f"int() sur {x.type} non supporté", node)

    def b_float(self, node):
        (x,) = self.need(node, 1)
        if x.type == STR:
            return ir.Call("float_str", [x], FLOAT, "builtin")
        if x.type == FLOAT:
            return x
        if x.type in (INT, BOOL):
            return ir.Cast(x, FLOAT)
        raise Unsupported(f"float() sur {x.type} non supporté", node)

    def b_str(self, node):
        (x,) = self.need(node, 1, keep_opt=True)
        return ir.Call("str", [self.need_printable(x, node)], STR, "builtin")

    def _minmax(self, node, name):
        kws = {k.arg: k.value for k in node.keywords}
        if set(kws) - {"key", "default"}:
            raise Unsupported(f"{name}() : seuls key= et default= sont supportés", node)
        args = [self.unopt(self.expr(a, view_ok=True)) for a in node.args]
        if kws:
            if len(args) == 1:
                lst = self.as_list(args[0], True)
            elif len(args) >= 2 and all(a.type == args[0].type for a in args):
                lst = ir.ListLit(args, list_of(args[0].type))
            else:
                raise Unsupported(f"{name}() : arguments de types différents", node)
            if lst.type.kind != "list":
                raise Unsupported(f"{name}() attend une liste, pas {lst.type}", node)
            et = lst.type.args[0]
            if "key" in kws:
                op = ir.KeyOp(name, [lst], self.key_lambda(kws["key"], et, node), ir.Const(False, BOOL), et)
            elif is_orderable(et):
                op = ir.Call(name + "_list", [lst], et, "builtin")
            else:
                raise Unsupported(f"{name}() sur des {et} sans key= non supporté", node)
            if "default" in kws:  # min(xs, default=d) : d si xs est vide
                if not self.is_pure(lst):
                    raise Unsupported(f"{name}(..., default=) : rangez d'abord la séquence dans une variable", node)
                d = self.coerce(self.expr(kws["default"], et), et, node)
                empty = ir.Cmp("==", ir.Call("len", [lst], INT, "builtin"), ir.Const(0, INT))
                return ir.Ternary(empty, d, op, et)
            return op
        if len(args) == 1:
            args = [self.as_list(args[0], True)]
        if len(args) == 1 and args[0].type.kind == "list" and is_orderable(args[0].type.args[0]):
            return ir.Call(name + "_list", args, args[0].type.args[0], "builtin")
        if len(args) >= 2 and all(a.type == args[0].type for a in args) and args[0].type in (INT, FLOAT, STR):
            return ir.Call(name, args, args[0].type, "builtin")
        if len(args) >= 2 and all(is_numeric(a.type) for a in args):
            raise Unsupported(f"{name}() mélange int et float : Python renvoie l'opérande d'origine, donc le type du résultat "
                              "dépend des valeurs (5 ou 5.0). Convertissez avec float(...) ou écrivez des constantes flottantes", node)
        raise Unsupported(f"{name}() : utilisez 2+ nombres/chaînes ou une liste de nombres", node)

    def b_min(self, node):
        return self._minmax(node, "min")

    def b_max(self, node):
        return self._minmax(node, "max")

    def b_sum(self, node):
        if len(node.args) not in (1, 2):
            raise Unsupported("sum() attend 1 ou 2 arguments", node)
        x = self.as_list(self.unopt(self.expr(node.args[0], view_ok=True)), True)
        if x.type.kind != "list" or not is_numeric(x.type.args[0]):
            raise Unsupported("sum() attend une liste de nombres", node)
        et = x.type.args[0]
        if len(node.args) == 2:  # sum(xs, départ) : Python additionne séquentiellement en partant de `départ`
            start = self.expr(node.args[1])
            if not is_numeric(start.type):
                raise Unsupported("le départ de sum() doit être un nombre", node)
            rt = INT if (et == INT and start.type == INT) else FLOAT
            return ir.Call("sum_start", [x, start if rt == start.type else self.promote(start)], rt, "builtin")
        return ir.Call("sum", [x], et, "builtin")

    def b_sorted(self, node):
        if len(node.args) != 1:
            raise Unsupported("sorted() attend 1 argument (+ key= et reverse=)", node)
        x = self.as_list(self.unopt(self.expr(node.args[0], view_ok=True)), True)
        if x.type.kind != "list":
            raise Unsupported(f"sorted() attend une liste, pas {x.type}", node)
        key, rev = self.sort_options(node, x.type.args[0])
        if key is None and isinstance(rev, ir.Const) and rev.value is False:
            if not is_orderable(x.type.args[0]):
                raise Unsupported("sorted() attend une liste d'int/float/str ou de tuples de ces types (ou une clé key=)", node)
            return ir.Call("sorted", [x], x.type, "builtin")
        return ir.KeyOp("sorted", [x], key or self.identity(x.type.args[0], node), rev, x.type)

    def method_call(self, node):
        f = node.func
        if self.is_super_call(f):
            return self.super_call(node)
        obj = self.obj_expr(f.value)
        m, t = f.attr, obj.type
        if t.kind == "class" and t.args[0] == "PyRandom" and m in ("choice", "sample", "choices"):
            return self.rnd_generic(f.value, m, node)
        if t.kind == "class":
            info = self.fe.classes[t.args[0]]
            found = self.fe.lookup_method(info.name, m)
            if found is None and self.fe.lookup_static(info.name, m) is not None:
                st = self.fe.lookup_static(info.name, m)
                if not self.is_pure(obj):
                    raise Unsupported(f"{m}() est une méthode statique : appelez-la sur la classe ({info.name}.{m}(...))", node)
                return self.user_call(st[0], node)
            fld = self.fe.lookup_field(info.name, m) if found is None else None
            if fld is not None and self.fe.resolve(fld[1][0]).kind == "func":  # self.handler(x) : champ de type Callable
                return self.call_value(ir.Attr(obj, m, self.fe.resolve(fld[1][0])), node)
            if found is None or m == "__init__":
                raise Unsupported(f"méthode {info.name}.{m}() inconnue", node)
            owner, (params, ret, defaults) = found
            args = self.bind_args(node, params, defaults, f"{info.name}.{m}()", callee=f"{owner.name}.{m}")
            return ir.UserMethodCall(obj, info.name, m, args, ret)
        if t == STR:
            return self.str_method(node, obj, m)
        if t == INT:
            return self.int_method(node, obj, m)
        if t.kind == "set":
            return self.set_method(node, obj, m)
        if t.kind == "deque":
            return self.deque_method(node, obj, m)
        if t.kind == "dict" and m in ("most_common", "total", "elements", "update", "move_to_end", "popitem"):
            r = self.dict_extra(node, obj, m)
            if r is not None:
                return r
        if t.kind == "list" and m == "sort":
            if node.args:
                raise Unsupported("sort() : key= et reverse= se passent par mot-clé", node)
            if not node.keywords and is_orderable(t.args[0]):
                self.note_mutation(obj)
                return ir.MethodCall(obj, "sort", [], NONE)
            key, rev = self.sort_options(node, t.args[0])
            self.note_mutation(obj)
            return ir.KeyOp("sort", [obj], key or self.identity(t.args[0], node), rev, NONE)
        if node.keywords:
            raise Unsupported(f".{m}() : arguments nommés non supportés", node)
        if t.kind == "list":
            if m == "copy" and not node.args:
                return ir.Call("list", [obj], t, "builtin")
            if m == "clear" and not node.args:
                self.note_mutation(obj)
                return ir.MethodCall(obj, "clear", [], NONE)
            if m == "append" and len(node.args) == 1:
                x = self.coerce(self.fresh(self.expr(node.args[0], t.args[0]), node), t.args[0], node)
                self.note_mutation(obj)
                return ir.MethodCall(obj, "append", [x], NONE)
            if m in ("sort", "reverse") and not node.args:
                if m == "sort" and not is_orderable(t.args[0]):
                    raise Unsupported("sort() attend une liste d'int/float/str ou de tuples de ces types", node)
                self.note_mutation(obj)
                return ir.MethodCall(obj, m, [], NONE)
            et = t.args[0]
            if m == "pop" and len(node.args) <= 1:
                i = self.coerce_int(self.expr(node.args[0]), node) if node.args else ir.Const(-1, INT)
                self.note_mutation(obj)
                return ir.MethodCall(obj, "pop", [i], et)
            if m == "extend" and len(node.args) == 1:
                x = self.expr(node.args[0], t, view_ok=True)
                if not self.fe.unify(x.type, t):
                    raise Unsupported(f"extend() attend une liste de même type ({t}), pas {x.type}", node)
                self.value_elems(t, "étendre avec", node)
                self.note_mutation(obj)
                return ir.MethodCall(obj, "extend", [x], NONE)
            if m == "insert" and len(node.args) == 2:
                i = self.coerce_int(self.expr(node.args[0]), node)
                x = self.coerce(self.fresh(self.expr(node.args[1], et), node), et, node)
                self.note_mutation(obj)
                return ir.MethodCall(obj, "insert", [i, x], NONE)
            if m in ("count", "index", "remove") and len(node.args) == 1:
                if not is_value_type(et):
                    raise Unsupported(f".{m}() sur une liste de {et} non supporté (comparaison de sous-listes)", node)
                x = self.coerce(self.expr(node.args[0], et), et, node)
                if m == "remove":
                    self.note_mutation(obj)
                return ir.MethodCall(obj, m, [x], NONE if m == "remove" else INT)
        if t.kind == "dict" and m in self.VIEWS and not node.args:
            k, v = t.args
            if m != "keys" and not is_value_type(v):
                raise Unsupported(f".{m}() sur un dict dont les valeurs sont de type {v} non supporté : en Python on obtiendrait "
                                  "des références partagées, ici des copies. Parcourez les clés : for k in d: ... d[k]", node)
            rt = {"keys": list_of(k), "values": list_of(v) if m == "values" else None,
                  "items": list_of(tuple_of(k, v)) if m == "items" else None}[m]
            return ir.MethodCall(obj, m, [], rt)
        if t.kind == "dict":
            kt, vt = t.args
            if m == "copy" and not node.args:
                return ir.MethodCall(obj, "copy", [], t)
            if m == "clear" and not node.args:
                return ir.MethodCall(obj, "clear", [], NONE)
            if m == "pop" and len(node.args) in (1, 2):
                k = self.coerce(self.expr(node.args[0], kt), kt, node)
                dflt = [self.coerce(self.expr(node.args[1], vt), vt, node)] if len(node.args) == 2 else []
                return ir.MethodCall(obj, "pop", [k] + dflt, vt)
            if m == "setdefault" and len(node.args) == 2:
                k = self.coerce(self.expr(node.args[0], kt), kt, node)
                d = self.coerce(self.expr(node.args[1], vt), vt, node)
                return ir.MethodCall(obj, "setdefault", [k, d], vt)
            if m == "update" and len(node.args) == 1:
                o = self.expr(node.args[0], t)
                if not self.fe.unify(o.type, t):
                    raise Unsupported(f"update() attend un dict de même type ({t}), pas {o.type}", node)
                return ir.MethodCall(obj, "update", [o], NONE)
            if m == "popitem" and not node.args:
                return ir.MethodCall(obj, "popitem", [], tuple_of(kt, vt))
        if t.kind == "dict" and m == "get" and len(node.args) == 1:
            k = self.coerce(self.expr(node.args[0], t.args[0]), t.args[0], node)
            return ir.MethodCall(obj, "get1", [k], optional_of(t.args[1]))
        if t.kind == "dict" and m == "get" and len(node.args) == 2:
            k = self.coerce(self.expr(node.args[0], t.args[0]), t.args[0], node)
            d = self.coerce(self.expr(node.args[1], t.args[1]), t.args[1], node)
            return ir.MethodCall(obj, "get", [k, d], t.args[1])
        raise Unsupported(f"méthode .{m}() non supportée sur le type {t}", node)

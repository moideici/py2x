"""Frontend : fonctions intégrées, méthodes de chaînes, formatage, tranches (slices) et suppressions (del).

Mixin de FuncConv : les méthodes utilisent self.expr(), self.coerce(), etc. de FuncConv.
"""
import ast
import re

from . import ir
from .errors import Unsupported
from .types import BOOL, FLOAT, INT, NONE, STR, class_of, dict_of, is_numeric, list_of, tuple_of

WS = " \t\n\r\x0b\x0c"


class GlobalDefault:
    """Valeur par défaut d'un paramètre qui désigne une constante de module (def f(m: int = MOD)) : lue à chaque appel."""

    def __init__(self, name):
        self.name = name


class BuiltinsMixin:
    # ------------------------------------------------------------------ outils
    def is_pure(self, e):
        if isinstance(e, (ir.Var, ir.Const, ir.LibConst)):
            return True
        if isinstance(e, ir.Attr):
            return self.is_pure(e.obj)
        if isinstance(e, ir.Unwrap):
            return self.is_pure(e.operand)
        if isinstance(e, ir.Index):
            return self.is_pure(e.base) and self.is_pure(e.index)
        if isinstance(e, ir.TupleGet):
            return self.is_pure(e.base)
        if isinstance(e, ir.Call) and (e.kind in ("str", "lib") or (e.kind == "builtin" and e.name in ("len", "abs", "str", "min", "max"))):
            return all(self.is_pure(a) for a in e.args)
        if isinstance(e, ir.Cast):
            return self.is_pure(e.operand)
        if isinstance(e, ir.Unary):
            return self.is_pure(e.operand)
        if isinstance(e, ir.BinOp):
            return self.is_pure(e.left) and self.is_pure(e.right)
        return False

    def as_list(self, e, unordered_ok=False):
        """Une chaîne s'itère caractère par caractère : on la convertit en liste de chaînes d'un caractère.
        deque -> instantané en liste ; set -> liste dans l'ordre de table de CPython (int) ; l'ordre d'un set de chaînes est
        aléatoire en Python : refusé sauf pour les consommateurs insensibles à l'ordre (sorted, min, max, sum)."""
        if e.type.kind == "gen":  # consomme le générateur (fini)
            return ir.Call("gen_list", [e], list_of(e.type.args[0]), "builtin")
        if e.type.kind == "tuple":  # tuple homogène : sum(t), max(t), sorted(t), list(t)...
            return self.tuple_as_list(e, None)
        if e.type.kind == "vtuple":
            return ir.Call("vt_list", [e], list_of(e.type.args[0]), "builtin")
        if e.type.kind == "deque":
            return ir.Call("dq_list", [e], list_of(e.type.args[0]), "builtin")
        if e.type.kind == "set":
            if not unordered_ok and e.type.args[0] not in (INT, BOOL):
                raise Unsupported(f"parcours d'un set de {e.type.args[0]} : son ordre varie d'une exécution à l'autre en Python "
                                  "(hachage aléatoire des chaînes) ; utilisez sorted(s)")
            return ir.Call("set_list", [e], list_of(e.type.args[0]), "builtin")
        if e.type == STR:
            return ir.Call("chars", [e], list_of(STR), "str")
        if e.type.kind == "dict":  # itérer sur un dict = itérer sur ses clés (sorted(d), list(d), max(d, key=...))
            return ir.MethodCall(e, "keys", [], list_of(e.type.args[0]))
        return e

    def tuple_as_list(self, e, node):
        """Un tuple HOMOGÈNE s'itère comme une liste : for d in (1, 2, 3) / x in (2, 3)."""
        ts = set(e.type.args)
        if len(ts) != 1 and isinstance(e, ir.TupleLit) and all(t.kind == "class" for t in ts):  # (Cercle(), Carre()) : liste de l'ancêtre commun
            lub = self.fe.lub_class([t.args[0] for t in ts])
            if lub is not None:
                return ir.ListLit(list(e.elems), list_of(class_of(lub)))
        if len(ts) != 1:
            raise Unsupported(f"itération/appartenance sur un tuple hétérogène {e.type} non supportée", node)
        et = e.type.args[0]
        if isinstance(e, ir.TupleLit):
            return ir.ListLit(list(e.elems), list_of(et))
        return ir.Call("tuple_list", [e], list_of(et), "builtin")

    # ------------------------------------------------------------------ méthodes de chaînes
    def str_method(self, node, obj, m):
        a, n = node.args, len(node.args)

        def need(lo, hi=None):
            hi = lo if hi is None else hi
            if not lo <= n <= hi:
                raise Unsupported(f".{m}() attend {lo if lo == hi else f'{lo} à {hi}'} argument(s), {n} fourni(s)", node)

        S = lambda i: self.coerce(self.expr(a[i]), STR, node)  # noqa: E731
        I = lambda i: self.coerce_int(self.expr(a[i]), node)  # noqa: E731
        call = lambda name, args, ret: ir.Call(name, [obj] + args, ret, "str")  # noqa: E731
        k = lambda v, t=STR: ir.Const(v, t)  # noqa: E731
        if node.keywords and m != "format":
            raise Unsupported(f".{m}() : arguments nommés non supportés", node)
        if m in ("upper", "lower", "capitalize", "title", "swapcase"):
            need(0)
            return call(m, [], STR)
        if m in ("strip", "lstrip", "rstrip"):
            need(0, 1)
            return call("strip", [S(0) if n else k(WS), k({"strip": 0, "lstrip": 1, "rstrip": 2}[m], INT)], STR)
        if m == "split":
            need(0, 2)
            if n == 0:
                return call("split_ws", [], list_of(STR))
            if isinstance(a[0], ast.Constant) and a[0].value is None:
                raise Unsupported("split(None, n) non supporté : utilisez split() ou split(sep, n)", node)
            return call("split", [S(0), I(1) if n == 2 else k(-1, INT)], list_of(STR))
        if m == "rsplit":
            need(0, 2)
            if n == 0 or (isinstance(a[0], ast.Constant) and a[0].value is None):
                return call("rsplit_ws", [I(1) if n == 2 else k(-1, INT)], list_of(STR))
            return call("rsplit", [S(0), I(1) if n == 2 else k(-1, INT)], list_of(STR))
        if m == "splitlines":
            need(0)
            return call("splitlines", [], list_of(STR))
        if m == "join":
            need(1)
            if isinstance(a[0], ast.GeneratorExp):
                self.allowed_gens.add(a[0])
            x = self.as_list(self.unopt(self.expr(a[0], view_ok=True)), True) if not isinstance(a[0], ast.GeneratorExp) else self.expr(a[0], view_ok=True)
            x = self.coerce(x, list_of(STR), node)
            return ir.Call("join", [obj, x], STR, "str")
        if m == "replace":
            need(2, 3)
            return call("replace", [S(0), S(1), I(2) if n == 3 else k(-1, INT)], STR)
        if m in ("startswith", "endswith"):
            need(1)
            return call(m, [S(0)], BOOL)
        if m in ("find", "rfind", "index", "count"):
            need(1)
            return call({"find": "find", "rfind": "rfind", "index": "sindex", "count": "scount"}[m], [S(0)], INT)
        if m in ("isdigit", "isalpha", "isalnum", "isspace", "islower", "isupper"):
            need(0)
            return call(m, [], BOOL)
        if m in ("isnumeric", "isdecimal"):
            need(0)
            return call("isdigit", [], BOOL)
        if m == "zfill":
            need(1)
            return call("zfill", [I(0)], STR)
        if m in ("ljust", "rjust", "center"):
            need(1, 2)
            return call(m, [I(0), S(1) if n == 2 else k(" ")], STR)
        if m in ("partition", "rpartition"):
            need(1)
            return call(m, [S(0)], tuple_of(STR, STR, STR))
        if m == "isascii":
            need(0)
            return call("isascii", [], BOOL)
        if m == "isidentifier":
            need(0)
            return call("isidentifier", [], BOOL)
        if m == "rindex":
            need(1)
            return call("srindex", [S(0)], INT)
        if m in ("removeprefix", "removesuffix"):
            need(1)
            return call(m, [S(0)], STR)
        if m == "format":
            return self.str_format(node, obj)
        raise Unsupported(f"méthode str.{m}() non supportée", node)

    def int_method(self, node, obj, m):
        if m in ("bit_length", "bit_count") and not node.args:
            return ir.Call(m, [obj], INT, "builtin")
        raise Unsupported(f"méthode int.{m}() non supportée", node)

    # ------------------------------------------------------------------ formatage
    def format_part(self, value, spec_expr, conv, node):
        """Un champ de format : valeur + spécification (expression str) + conversion (!r/!s) -> expression str."""
        if conv == "r":
            value = ir.Call("repr", [self.need_printable_nested(value, node)], STR, "builtin")
        elif conv == "s":
            value = ir.Call("str", [self.need_printable(value, node)], STR, "builtin")
        elif conv not in (None, ""):
            raise Unsupported(f"conversion !{conv} non supportée dans un format", node)
        empty = isinstance(spec_expr, ir.Const) and spec_expr.value == ""
        if empty:
            return value if value.type == STR else ir.Call("str", [self.need_printable(value, node)], STR, "builtin")
        if value.type not in (INT, FLOAT, STR, BOOL):
            raise Unsupported(f"format avec spécification sur le type {value.type} non supporté (int, float, str, bool seulement)", node)
        return ir.Call("format", [value, spec_expr], STR, "builtin")

    def need_printable_nested(self, e, node):
        if not self.printable(e.type, True):
            raise Unsupported(f"repr() d'un objet de type {e.type} sans __repr__ (ni @dataclass) non supporté", node)
        return e

    def concat(self, parts):
        if not parts:
            return ir.Const("", STR)
        e = parts[0]
        for p in parts[1:]:
            e = ir.BinOp("+", e, p, STR)
        return e

    FIELD = re.compile(r"\{\{|\}\}|\{([^{}!:]*)(?:!([a-z]))?(?::([^{}]*))?\}")

    def str_format(self, node, fmt_obj):
        """"{} {:.2f} {name}".format(a, b, name=c) : le format doit être un LITTÉRAL (désucré à la compilation)."""
        if not isinstance(fmt_obj, ir.Const):
            raise Unsupported("str.format() n'est supporté que sur un littéral de chaîne", node)
        args = [self.expr(x) for x in node.args]
        kwargs = {kw.arg: self.expr(kw.value) for kw in node.keywords if kw.arg}
        parts, auto, used_explicit = [], 0, False
        text = fmt_obj.value
        pos = 0
        for m in self.FIELD.finditer(text):
            if m.start() > pos:
                parts.append(ir.Const(text[pos:m.start()], STR))
            pos = m.end()
            if m.group(0) == "{{":
                parts.append(ir.Const("{", STR))
                continue
            if m.group(0) == "}}":
                parts.append(ir.Const("}", STR))
                continue
            name, conv, spec = m.group(1), m.group(2), m.group(3) or ""
            if name == "":
                if used_explicit:
                    raise Unsupported("format : mélange de champs automatiques {} et numérotés {0}", node)
                idx, auto = auto, auto + 1
                val = args[idx] if idx < len(args) else self.fail(node, "format : pas assez d'arguments")
            elif name.isdigit():
                used_explicit = True
                val = args[int(name)] if int(name) < len(args) else self.fail(node, "format : indice d'argument inconnu")
            elif name in kwargs:
                val = kwargs[name]
            else:
                raise Unsupported(f"format : champ {{{name}}} inconnu (attributs/indices dans un champ non supportés)", node)
            parts.append(self.format_part(val, ir.Const(spec, STR), conv, node))
        if pos < len(text):
            parts.append(ir.Const(text[pos:], STR))
        stray = re.sub(r"\{\{|\}\}", "", text)
        if "{" in self.FIELD.sub("", stray) or "}" in self.FIELD.sub("", stray):
            raise Unsupported("format : accolade isolée ou champ complexe non supporté", node)
        return self.concat(parts)

    def fail(self, node, msg):
        raise Unsupported(msg, node)

    PCT = re.compile(r"%(?:\(([^)]*)\))?([-+ #0]*)(\d+)?(?:\.(\d+))?([diouxXeEfFgGcrs%])")

    def percent_format(self, node, left, right_node):
        """"%d items, %.2f%%" % (a, b) : format littéral désucré à la compilation."""
        if not isinstance(left, ir.Const):
            raise Unsupported("l'opérateur % de formatage n'est supporté que sur un littéral de chaîne", node)
        if isinstance(right_node, ast.Tuple):
            vals = [self.expr(x) for x in right_node.elts]
        else:
            vals = [self.expr(right_node)]
        text, parts, pos, i = left.value, [], 0, 0
        for m in self.PCT.finditer(text):
            if m.start() > pos:
                parts.append(ir.Const(text[pos:m.start()], STR))
            pos = m.end()
            key, flags, width, prec, ty = m.groups()
            if key is not None:
                raise Unsupported("format % avec clés (%(nom)s) non supporté", node)
            if ty == "%":
                parts.append(ir.Const("%", STR))
                continue
            if i >= len(vals):
                raise Unsupported("format % : pas assez d'arguments", node)
            v, i = vals[i], i + 1
            spec = ""
            if "-" in flags:
                spec += "<"
            elif ty in "sr":
                spec += ">"  # %10s aligne à droite (contrairement à {:10} qui aligne les chaînes à gauche)
            if "+" in flags:
                spec += "+"
            elif " " in flags:
                spec += " "
            if "#" in flags:
                spec += "#"
            if "0" in flags and "-" not in flags:
                spec += "0"
            spec += (width or "") + ("." + prec if prec is not None else "")
            if ty in "di":
                if v.type == FLOAT:
                    v = ir.Cast(v, INT)
                spec += "d"
            elif ty in "ouxX":
                spec += {"o": "o", "u": "d", "x": "x", "X": "X"}[ty]
            elif ty in "eEfFgG":
                v = self.promote(v)
                spec += ty
            elif ty == "c":
                raise Unsupported("%c non supporté", node)
            elif ty == "r":
                v = ir.Call("repr", [self.need_printable_nested(v, node)], STR, "builtin")
                spec += "s"
            else:  # s
                v = ir.Call("str", [self.need_printable(v, node)], STR, "builtin") if v.type != STR else v
                spec += "s"
            parts.append(ir.Call("format", [v, ir.Const(spec, STR)], STR, "builtin"))
        if pos < len(text):
            parts.append(ir.Const(text[pos:], STR))
        if i != len(vals):
            raise Unsupported("format % : trop d'arguments", node)
        if "%" in self.PCT.sub("", text.replace("%%", "")):
            raise Unsupported("format % : spécification non supportée", node)
        return self.concat(parts)

    # ------------------------------------------------------------------ fonctions intégrées
    def b_round(self, node):
        if len(node.args) not in (1, 2):
            raise Unsupported("round() attend 1 ou 2 arguments", node)
        x = self.expr(node.args[0])
        if len(node.args) == 1:
            if x.type == INT:
                return x
            if x.type == FLOAT:
                return ir.Call("round", [x], INT, "builtin")
            raise Unsupported(f"round() sur {x.type} non supporté", node)
        n = self.coerce_int(self.expr(node.args[1]), node)
        if x.type == FLOAT:
            return ir.Call("round_n", [x, n], FLOAT, "builtin")
        raise Unsupported("round(entier, n) non supporté (utilisez round(float, n))", node)

    def b_divmod(self, node):
        a, b = self.need(node, 2)
        if a.type != INT or b.type != INT:
            raise Unsupported("divmod() n'est supporté que sur des entiers", node)
        if not (self.is_pure(a) and self.is_pure(b)):
            raise Unsupported("divmod() avec un argument à effet de bord : rangez-le d'abord dans une variable", node)
        return ir.TupleLit([ir.BinOp("//", a, b, INT), ir.BinOp("%", a, b, INT)], tuple_of(INT, INT))

    def b_pow(self, node):
        if len(node.args) == 2:
            a, b = self.need(node, 2)
            return self.binop("**", a, b, node)
        a, b, m = self.need(node, 3)
        if not (a.type == INT and b.type == INT and m.type == INT):
            raise Unsupported("pow(a, b, mod) n'est supporté que sur des entiers", node)
        return ir.Call("powmod", [a, b, m], INT, "builtin")

    def _based(self, node, name):
        (x,) = self.need(node, 1)
        if x.type != INT:
            raise Unsupported(f"{name}() attend un entier", node)
        return ir.Call(name, [x], STR, "builtin")

    def b_bin(self, node):
        return self._based(node, "bin")

    def b_hex(self, node):
        return self._based(node, "hex")

    def b_oct(self, node):
        return self._based(node, "oct")

    def b_ord(self, node):
        (x,) = self.need(node, 1)
        return ir.Call("ord", [self.coerce(x, STR, node)], INT, "builtin")

    def b_chr(self, node):
        (x,) = self.need(node, 1)
        return ir.Call("chr", [self.coerce_int(x, node)], STR, "builtin")

    def b_bool(self, node):
        (x,) = self.need(node, 1, keep_opt=True)
        return self.truthy(x)

    def b_format(self, node):
        if len(node.args) not in (1, 2):
            raise Unsupported("format() attend 1 ou 2 arguments", node)
        v = self.expr(node.args[0])
        spec = self.coerce(self.expr(node.args[1]), STR, node) if len(node.args) == 2 else ir.Const("", STR)
        return self.format_part(v, spec, None, node)

    def b_repr(self, node):
        (x,) = self.need(node, 1, keep_opt=True)
        return ir.Call("repr", [self.need_printable_nested(x, node)], STR, "builtin")

    def b_input(self, node):
        if len(node.args) > 1:
            raise Unsupported("input() attend au plus un argument", node)
        prompt = self.coerce(self.expr(node.args[0]), STR, node) if node.args else ir.Const("", STR)
        return ir.Call("input", [prompt], STR, "builtin")

    # ------------------------------------------------------------------ tranches et suppressions
    def slice_parts(self, sl, node):
        def part(p):
            return None if p is None else self.coerce_int(self.expr(p), node)
        step = part(sl.step)
        if isinstance(step, ir.Const) and step.value == 0:
            raise Unsupported("pas de tranche nul", node)
        return part(sl.lower), part(sl.upper), step

    def slice_expr(self, node, base):
        t = base.type
        if t.kind != "list" and t != STR:
            raise Unsupported(f"découpage non supporté sur le type {t}", node)
        lo, hi, step = self.slice_parts(node.slice, node)
        return ir.Slice(base, lo, hi, step, t)

    def s_Delete(self, node):
        out = []
        for t in node.targets:
            if not isinstance(t, ast.Subscript):
                raise Unsupported("`del` n'est supporté que sur un élément, une tranche ou une clé (del xs[i], del d[k])", node)
            base = self.unopt(self.expr(t.value))
            if isinstance(t.slice, ast.Slice):
                if base.type.kind != "list":
                    raise Unsupported("del sur une tranche : listes seulement", node)
                lo, hi, step = self.slice_parts(t.slice, node)
                out.append(ir.Delete("slice", base, [lo, hi, step]))
            elif base.type.kind == "list":
                out.append(ir.Delete("item", base, [self.coerce_int(self.expr(t.slice), node)]))
            elif base.type.kind == "dict":
                out.append(ir.Delete("key", base, [self.coerce(self.expr(t.slice, base.type.args[0]), base.type.args[0], node)]))
            else:
                raise Unsupported(f"del sur le type {base.type} non supporté", node)
        return out

"""Frontend des collections : deque, set, Counter / defaultdict / OrderedDict, heapq.

Les set d'entiers reproduisent l'ordre d'itération de CPython (table de hachage émulée dans les runtimes) ; ceux de
chaînes/tuples ne peuvent pas être parcourus (leur ordre varie d'une exécution à l'autre en Python) : sorted(s), len, in... restent permis."""
import ast

from . import ir
from .errors import Unsupported
from .types import (BOOL, FLOAT, INT, NONE, STR, deque_of, dict_of, func_of, has_pending, is_hashable, is_orderable, list_of,
                    set_of, tuple_of)

COLL_MODULES = {"collections", "heapq", "functools"}
COLL_NAMES = {
    "collections": {"deque", "defaultdict", "Counter", "OrderedDict"},
    "heapq": {"heappush", "heappop", "heapify", "heapreplace", "heappushpop", "nlargest", "nsmallest"},
    "functools": {"reduce", "lru_cache", "cache"},
}
FACTORY_REPR = {"int": "<class 'int'>", "float": "<class 'float'>", "str": "<class 'str'>", "bool": "<class 'bool'>",
                "list": "<class 'list'>", "dict": "<class 'dict'>", "set": "<class 'set'>"}


def _ok_elem(t):
    return has_pending(t) or is_hashable(t)


class CollectionsMixin:
    # ---------- constructeurs ----------
    def coll_call(self, name, node, expected=None):
        h = getattr(self, "c_" + name, None)
        if h is None:
            raise Unsupported(f"{name}() non supporté", node)
        return h(node, expected)

    def c_deque(self, node, expected):
        kws = {k.arg: k.value for k in node.keywords}
        if set(kws) - {"maxlen"} or len(node.args) > 2:
            raise Unsupported("deque(iterable, maxlen) : seuls ces arguments sont supportés", node)
        ml = node.args[1] if len(node.args) == 2 else kws.get("maxlen")
        if ml is None or (isinstance(ml, ast.Constant) and ml.value is None):
            maxlen = ir.Const(-1, INT)
        else:
            maxlen = self.coerce_int(self.expr(ml), node)
        et = expected.args[0] if expected is not None and expected.kind == "deque" else None
        if node.args:
            x = self.as_list(self.unopt(self.expr(node.args[0], list_of(et) if et else None, view_ok=True)))
            if x.type.kind != "list":
                raise Unsupported(f"deque() attend une liste (ou une chaîne), pas {x.type}", node)
            return ir.Call("deque_from", [x, maxlen], deque_of(x.type.args[0]), "builtin")
        return ir.Call("deque_new", [maxlen], deque_of(et or self.empty_hint(node, "elem")), "builtin")

    def c_set(self, node, expected):
        if node.keywords or len(node.args) > 1:
            raise Unsupported("set() attend au plus un argument", node)
        et = expected.args[0] if expected is not None and expected.kind == "set" else None
        if not node.args:
            t = set_of(et or self.empty_hint(node, "elem"))
            return ir.Call("set_new", [], t, "builtin")
        x = self.unopt(self.expr(node.args[0], None, view_ok=True))
        if x.type.kind == "set":
            return ir.Call("set_copy", [x], x.type, "builtin")
        x = self.as_list(x)
        if x.type.kind != "list":
            raise Unsupported(f"set() attend une liste, une chaîne ou un set, pas {x.type}", node)
        if not _ok_elem(x.type.args[0]):
            raise Unsupported(f"set de {x.type.args[0]} non supporté : éléments int, str, bool ou tuples de ces types", node)
        return ir.Call("set_from", [x], set_of(x.type.args[0]), "builtin")

    def e_Set(self, node, expected=None):
        et = expected.args[0] if expected is not None and expected.kind == "set" else None
        elems = [self.expr(e, et) for e in node.elts]
        et = et or elems[0].type
        if not _ok_elem(et):
            raise Unsupported(f"set de {et} non supporté : éléments int, str, bool ou tuples de ces types", node)
        elems = [self.coerce(e, et, node) for e in elems]
        folded = len(node.elts) >= 3 and all(isinstance(e, ast.Constant) for e in node.elts)  # CPython : frozenset constant fusionné
        return ir.Call("set_lit_folded" if folded else "set_lit", [ir.ListLit(elems, list_of(et))], set_of(et), "builtin")

    def e_SetComp(self, node, expected=None):
        lst = self.comp(node, "list", list_of(expected.args[0]) if expected is not None and expected.kind == "set" else None)
        if not _ok_elem(lst.type.args[0]):
            raise Unsupported(f"set de {lst.type.args[0]} non supporté : éléments int, str, bool ou tuples de ces types", node)
        return ir.Call("set_from", [lst], set_of(lst.type.args[0]), "builtin")

    def c_defaultdict(self, node, expected):
        if node.keywords or len(node.args) != 1:
            raise Unsupported("defaultdict(fabrique) : un seul argument, int/float/str/bool/list/dict/set", node)
        f = node.args[0]
        if not (isinstance(f, ast.Name) and f.id in FACTORY_REPR):
            raise Unsupported("defaultdict : la fabrique doit être int, float, str, bool, list, dict ou set (lambda non supporté)", node)
        kt = vt = None
        if expected is not None and expected.kind == "dict":
            kt, vt = expected.args
        kt = kt or self.empty_hint(node, "k")
        want = {"int": INT, "float": FLOAT, "str": STR, "bool": BOOL}.get(f.id)
        if vt is None:
            if want is not None:
                vt = want
            elif f.id == "list":
                vt = list_of(self.empty_hint(node, "ve"))
            elif f.id == "set":
                vt = set_of(self.empty_hint(node, "ve"))
            else:
                vt = dict_of(self.empty_hint(node, "vk"), self.empty_hint(node, "vv"))
        elif (want is not None and vt != want) or (want is None and vt.kind != f.id):
            raise Unsupported(f"defaultdict({f.id}) incompatible avec le type annoté {expected}", node)
        return ir.DictNew(1, FACTORY_REPR[f.id], dict_of(kt, vt))

    def c_Counter(self, node, expected):
        if node.keywords or len(node.args) > 1:
            raise Unsupported("Counter() attend au plus un argument (une liste ou une chaîne)", node)
        if not node.args:
            kt = expected.args[0] if expected is not None and expected.kind == "dict" else self.empty_hint(node, "k")
            return ir.DictNew(2, "", dict_of(kt, INT))
        x = self.as_list(self.unopt(self.expr(node.args[0], None, view_ok=True)))
        if x.type.kind != "list" or not _ok_elem(x.type.args[0]):
            raise Unsupported(f"Counter() attend une liste (ou une chaîne) d'éléments hachables, pas {x.type}", node)
        return ir.Call("counter_from", [x], dict_of(x.type.args[0], INT), "builtin")

    def c_OrderedDict(self, node, expected):
        if node.args or node.keywords:
            raise Unsupported("OrderedDict() sans argument seulement (remplissez-le ensuite avec d[k] = v)", node)
        if expected is not None and expected.kind == "dict":
            return ir.DictNew(3, "", expected)
        return ir.DictNew(3, "", dict_of(self.empty_hint(node, "k"), self.empty_hint(node, "v")))

    def c_reduce(self, node, expected):
        if len(node.args) not in (2, 3) or node.keywords:
            raise Unsupported("reduce(f, itérable[, départ]) attend 2 ou 3 arguments positionnels", node)
        xs = self.as_list(self.unopt(self.expr(node.args[1], view_ok=True)))
        if xs.type.kind != "list":
            raise Unsupported(f"reduce() attend une liste, pas {xs.type}", node)
        et = xs.type.args[0]
        init = self.expr(node.args[2]) if len(node.args) == 3 else None
        acc = et if init is None else init.type
        fn = self.expr(node.args[0], func_of([acc, et], acc))
        if fn.type != func_of([acc, et], acc):
            raise Unsupported(f"reduce : la fonction doit être ({acc}, {et}) -> {acc}, pas {fn.type}", node)
        if init is None:
            return ir.Call("reduce", [xs, fn], acc, "builtin")
        return ir.Call("reduce_init", [xs, init, fn], acc, "builtin")

    # ---------- heapq ----------
    def heap_arg(self, node, n):
        if len(node.args) != n or node.keywords:
            raise Unsupported(f"{ast.unparse(node.func)}() attend {n} argument(s) positionnel(s)", node)
        h = self.unopt(self.expr(node.args[0]))
        if h.type.kind != "list":
            raise Unsupported(f"heapq opère sur une liste, pas {h.type}", node)
        et = self.fe.resolve(h.type.args[0])
        if not has_pending(et) and not is_orderable(et):
            raise Unsupported(f"heapq sur des éléments {et} non comparables (int, float, str ou tuples de ces types)", node)
        return h, et

    def c_heappush(self, node, expected):
        h, et = self.heap_arg(node, 2)
        x = self.coerce(self.expr(node.args[1], et), et, node)
        self.note_mutation(h)
        return ir.Call("heappush", [h, x], NONE, "builtin")

    def c_heappop(self, node, expected):
        h, et = self.heap_arg(node, 1)
        self.note_mutation(h)
        return ir.Call("heappop", [h], et, "builtin")

    def c_heapify(self, node, expected):
        h, et = self.heap_arg(node, 1)
        self.note_mutation(h)
        return ir.Call("heapify", [h], NONE, "builtin")

    def c_heapreplace(self, node, expected):
        h, et = self.heap_arg(node, 2)
        x = self.coerce(self.expr(node.args[1], et), et, node)
        self.note_mutation(h)
        return ir.Call("heapreplace", [h, x], et, "builtin")

    def c_heappushpop(self, node, expected):
        h, et = self.heap_arg(node, 2)
        x = self.coerce(self.expr(node.args[1], et), et, node)
        self.note_mutation(h)
        return ir.Call("heappushpop", [h, x], et, "builtin")

    def nbest(self, node, name):
        if len(node.args) != 2 or node.keywords:
            raise Unsupported(f"{name}(n, iterable) : key= non supporté", node)
        n = self.coerce_int(self.expr(node.args[0]), node)
        x = self.as_list(self.unopt(self.expr(node.args[1], view_ok=True)), True)
        if x.type.kind != "list" or not is_orderable(x.type.args[0]):
            raise Unsupported(f"{name}() attend une liste d'int/float/str ou de tuples de ces types", node)
        return ir.Call(name, [n, x], x.type, "builtin")

    def c_nlargest(self, node, expected):
        return self.nbest(node, "nlargest")

    def c_nsmallest(self, node, expected):
        return self.nbest(node, "nsmallest")

    # ---------- méthodes ----------
    def set_method(self, node, obj, m):
        t, a = obj.type, node.args
        et = t.args[0]
        if node.keywords:
            raise Unsupported(f".{m}() : arguments nommés non supportés", node)

        def E(i):
            return self.coerce(self.expr(a[i], et), et, node)

        def call(name, args, ret=NONE):
            return ir.Call(name, [obj] + args, ret, "builtin")

        def other():
            o = self.unopt(self.expr(a[0], t, view_ok=True))
            if not self.fe.unify(o.type, t):
                raise Unsupported(f".{m}() attend un set de même type ({t}), pas {o.type}", node)
            return o

        if m in ("add", "remove", "discard") and len(a) == 1:
            self.note_mutation(obj)
            return call("set_" + m, [E(0)])
        if m == "pop" and not a:
            self.note_mutation(obj)
            return call("set_pop", [], et)
        if m == "clear" and not a:
            self.note_mutation(obj)
            return call("set_clear", [])
        if m == "copy" and not a:
            return call("set_copy", [], t)
        if m == "update" and len(a) == 1:
            x = self.unopt(self.expr(a[0], t, view_ok=True))
            if x.type.kind == "set":
                ok = self.fe.unify(x.type, t)
            else:
                x = self.as_list(x)
                ok = x.type.kind == "list" and self.fe.unify(x.type, list_of(et))
            if not ok:
                raise Unsupported(f"update() attend un set ou une liste de {et}, pas {x.type}", node)
            self.note_mutation(obj)
            return call("set_update", [x])
        names = {"union": "set_union", "intersection": "set_inter", "difference": "set_diff", "symmetric_difference": "set_symdiff"}
        if m in names and len(a) == 1:
            return call(names[m], [other()], t)
        if m == "issubset" and len(a) == 1:
            return call("set_issubset", [other()], BOOL)
        if m == "issuperset" and len(a) == 1:
            return ir.Call("set_issubset", [other(), obj], BOOL, "builtin")
        if m == "isdisjoint" and len(a) == 1:
            return call("set_isdisjoint", [other()], BOOL)
        raise Unsupported(f"méthode .{m}() non supportée sur le type {t}", node)

    def deque_method(self, node, obj, m):
        t, a = obj.type, node.args
        et = t.args[0]
        if node.keywords:
            raise Unsupported(f".{m}() : arguments nommés non supportés", node)

        def call(name, args, ret=NONE):
            return ir.Call(name, [obj] + args, ret, "builtin")

        if m in ("append", "appendleft") and len(a) == 1:
            x = self.coerce(self.expr(a[0], et), et, node)
            self.note_mutation(obj)
            return call("dq_" + m, [x])
        if m in ("pop", "popleft") and not a:
            self.note_mutation(obj)
            return call("dq_" + m, [], et)
        if m in ("extend", "extendleft") and len(a) == 1:
            x = self.as_list(self.unopt(self.expr(a[0], list_of(et), view_ok=True)))
            if x.type.kind != "list" or not self.fe.unify(x.type, list_of(et)):
                raise Unsupported(f"{m}() attend une liste de {et}, pas {x.type}", node)
            self.note_mutation(obj)
            return call("dq_" + m, [x])
        if m in ("clear", "reverse") and not a:
            self.note_mutation(obj)
            return call("dq_" + m, [])
        if m == "rotate" and len(a) <= 1:
            n = self.coerce_int(self.expr(a[0]), node) if a else ir.Const(1, INT)
            self.note_mutation(obj)
            return call("dq_rotate", [n])
        if m == "copy" and not a:
            return call("dq_copy", [], t)
        raise Unsupported(f"méthode .{m}() non supportée sur le type {t}", node)

    def dict_extra(self, node, obj, m):
        """Méthodes de Counter / OrderedDict (le comportement par défaut vit dans le dict à l'exécution)."""
        t = obj.type
        kt, vt = t.args
        a = node.args
        kws = {k.arg: k.value for k in node.keywords}
        if m == "most_common" and len(a) <= 1 and not kws and vt == INT:
            n = self.coerce_int(self.expr(a[0]), node) if a else ir.Const(-1, INT)
            return ir.Call("most_common", [obj, n], list_of(tuple_of(kt, INT)), "builtin")
        if m == "total" and not a and not kws and vt == INT:
            return ir.Call("counter_total", [obj], INT, "builtin")
        if m == "elements" and not a and not kws and vt == INT:
            return ir.Call("counter_elements", [obj], list_of(kt), "builtin")
        if m == "update" and len(a) == 1 and not kws and vt == INT:
            x = self.unopt(self.expr(a[0], None, view_ok=True))
            if x.type.kind != "dict":  # Counter.update(itérable) : compte les éléments
                x = self.as_list(x)
                if x.type.kind == "list" and self.fe.unify(x.type, list_of(kt)):
                    return ir.Call("counter_update", [obj, x], NONE, "builtin")
        if m in ("move_to_end", "popitem") and set(kws) <= {"last"}:
            last = kws.get("last")
            lastc = ir.Const(True, BOOL) if last is None else self.coerce(self.expr(last), BOOL, node)
            if m == "move_to_end" and len(a) == 1:
                k = self.coerce(self.expr(a[0], kt), kt, node)
                return ir.Call("move_to_end", [obj, k, lastc], NONE, "builtin")
            if m == "popitem" and not a:
                return ir.Call("popitem_at", [obj, lastc], tuple_of(kt, vt), "builtin")
        return None

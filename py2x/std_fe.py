"""Frontend : bisect, itertools, lru_cache/cache, sys.stdin/stdout, dict.fromkeys."""
import ast

from . import ir
from .errors import Unsupported
from .coll_fe import COLL_MODULES, COLL_NAMES
from .types import BOOL, FLOAT, INT, NONE, STR, class_of, func_of, is_orderable, list_of, tuple_of, vtuple_of

STD_MODULES = {"bisect", "itertools", "random"}
STD_NAMES = {
    "bisect": {"bisect_left", "bisect_right", "bisect", "insort_left", "insort_right", "insort"},
    "itertools": {"product", "permutations", "combinations", "combinations_with_replacement", "accumulate", "chain", "islice",
                  "pairwise", "repeat"},
    "random": {"seed", "random", "randint", "randrange", "uniform", "gauss", "expovariate", "getrandbits", "choice", "shuffle",
               "sample", "choices", "Random"},
}


COLL_MODULES |= STD_MODULES
COLL_NAMES.update(STD_NAMES)


class StdMixin:
    def seq(self, node, unordered=False):
        x = self.unopt(self.expr(node, view_ok=True))
        if x.type.kind == "tuple":
            x = self.tuple_as_list(x, node)
        x = self.as_list(x, unordered)
        if x.type.kind != "list":
            raise Unsupported(f"itérable attendu (liste, chaîne, set...), pas {x.type}", node)
        return x

    # ---------- bisect ----------
    def bisect_args(self, node, name, nargs=2):
        if len(node.args) != nargs or node.keywords:
            raise Unsupported(f"{name}(liste, x) : 2 arguments positionnels seulement (lo/hi/key non supportés)", node)
        xs = self.unopt(self.expr(node.args[0]))
        if xs.type.kind != "list":
            raise Unsupported(f"{name}() attend une liste, pas {xs.type}", node)
        et = self.fe.resolve(xs.type.args[0])
        if not is_orderable(et):
            raise Unsupported(f"{name}() sur des {et} non comparables", node)
        return xs, self.coerce(self.expr(node.args[1], et), et, node)

    def c_bisect_left(self, node, expected):
        xs, x = self.bisect_args(node, "bisect_left")
        return ir.Call("bisect_left", [xs, x], INT, "builtin")

    def c_bisect_right(self, node, expected):
        xs, x = self.bisect_args(node, "bisect_right")
        return ir.Call("bisect_right", [xs, x], INT, "builtin")

    c_bisect = c_bisect_right

    def c_insort_left(self, node, expected):
        xs, x = self.bisect_args(node, "insort_left")
        self.note_mutation(xs)
        return ir.Call("insort_left", [xs, x], NONE, "builtin")

    def c_insort_right(self, node, expected):
        xs, x = self.bisect_args(node, "insort_right")
        self.note_mutation(xs)
        return ir.Call("insort_right", [xs, x], NONE, "builtin")

    c_insort = c_insort_right

    # ---------- itertools ----------
    def fixed_tuples(self, vecs, et, r, node):
        """list[vtuple[T]] -> list[tuple[T, ...]] quand la taille r est une constante (les tuples sont alors dépaquetables)."""
        if r is None or not 1 <= r <= 8:
            return vecs
        return ir.Call("vt_to_tuples", [vecs], list_of(tuple_of(*([et] * r))), "builtin")

    def const_r(self, a, node):
        r = self.const_int(a)
        if r is None:
            return None
        if r < 0:
            raise Unsupported("l'argument r doit être positif", node)
        return r

    def c_product(self, node, expected):
        kws = {k.arg: k.value for k in node.keywords}
        if set(kws) - {"repeat"}:
            raise Unsupported("product(*itérables, repeat=n) : seul repeat= est supporté", node)
        lists = [self.seq(a) for a in node.args]
        if "repeat" in kws:
            rep = self.const_r(kws["repeat"], node)
            if rep is None or len(lists) != 1:
                raise Unsupported("product(xs, repeat=n) : n constant et un seul itérable", node)
            et = lists[0].type.args[0]
            vecs = ir.Call("product_rep", [lists[0], ir.Const(rep, INT)], list_of(vtuple_of(et)), "builtin")
            return self.fixed_tuples(vecs, et, rep, node)
        if not 2 <= len(lists) <= 3:
            raise Unsupported("product() : 2 ou 3 itérables (ou un itérable avec repeat=)", node)
        t = tuple_of(*[x.type.args[0] for x in lists])
        return ir.Call(f"product{len(lists)}", lists, list_of(t), "builtin")

    def combo(self, node, name, with_r=True):
        if node.keywords or not (1 <= len(node.args) <= 2) or (with_r and name != "permutations" and len(node.args) != 2):
            raise Unsupported(f"{name}(itérable, r) : arguments positionnels", node)
        xs = self.seq(node.args[0])
        et = xs.type.args[0]
        r = self.const_r(node.args[1], node) if len(node.args) == 2 else None
        rarg = self.coerce_int(self.expr(node.args[1]), node) if len(node.args) == 2 else ir.Const(-1, INT)
        vecs = ir.Call(name + "_vec", [xs, rarg], list_of(vtuple_of(et)), "builtin")
        return self.fixed_tuples(vecs, et, r, node)

    def c_permutations(self, node, expected):
        return self.combo(node, "permutations")

    def c_combinations(self, node, expected):
        return self.combo(node, "combinations")

    def c_combinations_with_replacement(self, node, expected):
        return self.combo(node, "combinations_with_replacement")

    def c_accumulate(self, node, expected):
        kws = {k.arg: k.value for k in node.keywords}
        if set(kws) - {"initial", "func"} or not 1 <= len(node.args) <= 2:
            raise Unsupported("accumulate(itérable[, func], initial=x)", node)
        xs = self.seq(node.args[0])
        et = xs.type.args[0]
        fnode = node.args[1] if len(node.args) == 2 else kws.get("func")
        if fnode is None:
            if et not in (INT, FLOAT, STR):
                raise Unsupported(f"accumulate() sans fonction : éléments int, float ou str (pas {et})", node)
            fn = self.expr(ast.parse("lambda a, b: a + b", mode="eval").body, func_of([et, et], et))
        else:
            fn = self.expr(fnode, func_of([et, et], et))
        if fn.type != func_of([et, et], et):
            raise Unsupported(f"accumulate : la fonction doit être ({et}, {et}) -> {et}", node)
        if "initial" in kws:
            init = self.coerce(self.expr(kws["initial"], et), et, node)
            return ir.Call("accumulate_init", [xs, init, fn], list_of(et), "builtin")
        return ir.Call("accumulate", [xs, fn], list_of(et), "builtin")

    def c_chain(self, node, expected):
        if node.keywords or not node.args:
            raise Unsupported("chain(a, b, ...) : arguments positionnels", node)
        lists = [self.seq(a) for a in node.args]
        out = lists[0]
        for nxt in lists[1:]:
            if not self.fe.unify(out.type, nxt.type):
                raise Unsupported(f"chain : types d'éléments différents ({out.type}, {nxt.type})", node)
            out = ir.BinOp("+", out, nxt, self.fe.resolve(out.type))
        if len(lists) == 1:
            out = ir.Call("list", [out], out.type, "builtin")
        return out

    def c_chain_from_iterable(self, node, expected):
        if node.keywords or len(node.args) != 1:
            raise Unsupported("chain.from_iterable(iterable_de_listes)", node)
        xs = self.seq(node.args[0])
        inner = self.fe.resolve(xs.type.args[0])
        if inner.kind not in ("list", "vtuple"):
            raise Unsupported(f"chain.from_iterable attend une liste de listes, pas {xs.type}", node)
        if inner.kind not in ("list", "vtuple"):
            raise Unsupported("chain.from_iterable : liste de listes ou de tuples seulement", node)
        return ir.Call("flatten", [xs], list_of(inner.args[0]), "builtin")

    def c_islice(self, node, expected):
        if node.keywords or not 2 <= len(node.args) <= 4:
            raise Unsupported("islice(itérable, stop) / islice(itérable, start, stop[, pas])", node)
        a = node.args
        probe = self.expr(a[0], view_ok=True)
        if probe.type.kind == "gen":  # islice(générateur, [début,] fin) : prend paresseusement les premiers éléments
            stop = self.coerce_int(self.expr(a[1] if len(a) == 2 else a[2]), node)
            taken = ir.Call("gen_take", [probe, stop], list_of(probe.type.args[0]), "builtin")
            if len(a) >= 3:
                taken = ir.Slice(taken, self.coerce_int(self.expr(a[1]), node), None, None, taken.type)
            return taken
        none = None
        if len(a) == 2:
            lo, hi, st = none, a[1], none
        else:
            lo, hi, st = a[1], a[2], (a[3] if len(a) == 4 else none)
        sub = ast.Subscript(value=a[0], slice=ast.Slice(lower=lo, upper=hi, step=st), ctx=ast.Load())
        return self.expr(ast.copy_location(ast.fix_missing_locations(sub), node), view_ok=True)

    def c_pairwise(self, node, expected):
        if node.keywords or len(node.args) != 1:
            raise Unsupported("pairwise(itérable)", node)
        xs = self.seq(node.args[0])
        et = xs.type.args[0]
        tail = ir.Slice(xs, ir.Const(1, INT), None, None, xs.type)
        return ir.Call("zip", [xs, tail], list_of(tuple_of(et, et)), "builtin")

    def c_repeat(self, node, expected):
        if node.keywords or len(node.args) != 2:
            raise Unsupported("repeat(x, n) : n est obligatoire (itérateur infini non supporté)", node)
        x = self.expr(node.args[0])
        n = self.coerce_int(self.expr(node.args[1]), node)
        return ir.BinOp("*", ir.ListLit([x], list_of(x.type)), n, list_of(x.type))

    # ---------- lru_cache / cache : réécriture en fonction + dictionnaire de mémoïsation ----------
    @staticmethod
    def memo_decorator(node):
        for d in node.decorator_list:
            f = d.func if isinstance(d, ast.Call) else d
            name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if name in ("lru_cache", "cache"):
                return True
        return False

    def memoize(self, node):
        if len(node.decorator_list) != 1:
            raise Unsupported("lru_cache/cache combiné à d'autres décorateurs non supporté", node)
        a = node.args
        if a.vararg or a.kwarg or a.kwonlyargs or a.defaults or node.returns is None or not a.args:
            raise Unsupported("@lru_cache : fonction à paramètres positionnels annotés, sans valeur par défaut, avec type de retour", node)
        if any(p.annotation is None for p in a.args):
            raise Unsupported("@lru_cache : tous les paramètres doivent être annotés", node)
        name = node.name
        names = [p.arg for p in a.args]
        ann = [ast.unparse(p.annotation) for p in a.args]
        key_t = ann[0] if len(ann) == 1 else f"tuple[{', '.join(ann)}]"
        key = names[0] if len(names) == 1 else f"({', '.join(names)})"
        ret = ast.unparse(node.returns)
        params = ", ".join(f"{n}: {t}" for n, t in zip(names, ann))
        src = (f"_memo_{name}: dict[{key_t}, {ret}] = {{}}\n\n\n"
               f"def {name}({params}) -> {ret}:\n"
               f"    __k = {key}\n"
               f"    if __k in _memo_{name}:\n"
               f"        return _memo_{name}[__k]\n"
               f"    __r = _{name}_impl({', '.join(names)})\n"
               f"    _memo_{name}[__k] = __r\n"
               f"    return __r\n")
        wrapper = ast.parse(src).body
        impl = node
        impl.decorator_list = []
        impl.name = f"_{name}_impl"
        for n in wrapper:
            ast.copy_location(n, node)
            for sub in ast.walk(n):
                if hasattr(sub, "lineno"):
                    sub.lineno = node.lineno
                    sub.end_lineno = node.lineno
        # le corps original appelle `name` (le wrapper) : la récursion passe par le cache, comme en Python
        return [wrapper[0], impl, wrapper[1]]

    # ---------- random : fonctions du prélude (Mersenne Twister de CPython) ----------
    RNG = "py_rng"

    def rnd_call(self, name, node):
        return self.user_call(f"random_{name}", node)

    def c_seed(self, node, expected):
        return self.rnd_call("seed", node)

    def c_random(self, node, expected):
        return self.rnd_call("random", node)

    def c_randint(self, node, expected):
        return self.rnd_call("randint", node)

    def c_randrange(self, node, expected):
        return self.rnd_call("randrange", node)

    def c_uniform(self, node, expected):
        return self.rnd_call("uniform", node)

    def c_gauss(self, node, expected):
        return self.rnd_call("gauss", node)

    def c_expovariate(self, node, expected):
        return self.rnd_call("expovariate", node)

    def c_getrandbits(self, node, expected):
        return self.rnd_call("getrandbits", node)

    def c_Random(self, node, expected):
        return self.construct("PyRandom", node)

    def c_choice(self, node, expected):
        return self.rnd_generic(ast.Name(id=self.RNG, ctx=ast.Load()), "choice", node)

    def c_sample(self, node, expected):
        return self.rnd_generic(ast.Name(id=self.RNG, ctx=ast.Load()), "sample", node)

    def c_choices(self, node, expected):
        return self.rnd_generic(ast.Name(id=self.RNG, ctx=ast.Load()), "choices", node)

    def c_shuffle(self, node, expected):
        raise Unsupported("random.shuffle() s'utilise comme instruction (il modifie la liste sur place)", node)

    def pure_ast(self, a):
        return (isinstance(a, (ast.Name, ast.Constant)) or (isinstance(a, ast.Attribute) and self.pure_ast(a.value))
                or (isinstance(a, ast.Subscript) and self.pure_ast(a.value) and self.pure_ast(a.slice))
                or (isinstance(a, ast.BinOp) and self.pure_ast(a.left) and self.pure_ast(a.right))
                or (isinstance(a, (ast.List, ast.Tuple)) and all(self.pure_ast(e) for e in a.elts))
                or (isinstance(a, ast.Call) and isinstance(a.func, ast.Name) and a.func.id in ("range", "len", "list", "sorted", "int", "abs")
                    and not a.keywords and all(self.pure_ast(x) for x in a.args)))

    def rnd_generic(self, recv, name, node):
        """choice / sample / choices : génériques sur le type des éléments, réécrits en indices tirés par le générateur."""
        a = node.args
        kws = {k.arg: k.value for k in node.keywords}
        u = ast.unparse
        r = u(recv)
        if not a or not all(self.pure_ast(x) for x in a) or not all(self.pure_ast(v) for v in kws.values()):
            raise Unsupported(f"{name}() : arguments simples (variables, attributs, constantes) attendus", node)
        xs = u(a[0])
        if name == "choice":
            if len(a) != 1 or kws:
                raise Unsupported("choice(sequence)", node)
            text = f"{xs}[{r}.randbelow(len({xs}))]"
        elif name == "sample":
            k = a[1] if len(a) == 2 else kws.get("k")
            if k is None or (len(a) == 2 and kws) or len(a) > 2 or set(kws) - {"k"}:
                raise Unsupported("sample(population, k)", node)
            text = f"[{xs}[__ri] for __ri in {r}.sample_idx(len({xs}), {u(k)})]"
        else:
            k = kws.get("k", ast.Constant(value=1))
            if len(a) > 1 or set(kws) - {"k", "weights"}:
                raise Unsupported("choices(population, weights=..., k=...) : seuls weights= et k= sont supportés", node)
            if "weights" in kws:
                text = f"[{xs}[__ri] for __ri in {r}.choices_weighted_idx([float(__rw) for __rw in {u(kws['weights'])}], {u(k)})]"
            else:
                text = f"[{xs}[__ri] for __ri in {r}.choices_idx(len({xs}), {u(k)})]"
        return self.expr(ast.copy_location(ast.parse(text, mode="eval").body, node))

    def shuffle_stmt(self, v):
        """random.shuffle(xs) / rng.shuffle(xs) en instruction : boucle de Fisher-Yates identique à celle de CPython."""
        f = v.func
        recv = None
        if isinstance(f, ast.Attribute) and f.attr == "shuffle":
            if self.module_of(f.value) == "random":
                recv = ast.Name(id=self.RNG, ctx=ast.Load())
            elif self.pure_ast(f.value) and not isinstance(f.value, ast.Constant):
                try:
                    t = self.expr(f.value).type
                except Unsupported:
                    return None
                if t.kind == "class" and t.args[0] == "PyRandom":
                    recv = f.value
        elif isinstance(f, ast.Name) and f.id not in self.scope and self.fe.from_imports.get(f.id) == "random.shuffle":
            recv = ast.Name(id=self.RNG, ctx=ast.Load())
        if recv is None:
            return None
        if len(v.args) != 1 or v.keywords or not self.pure_ast(v.args[0]):
            raise Unsupported("shuffle(liste) : un argument simple (variable ou attribut)", v)
        xs, r = ast.unparse(v.args[0]), ast.unparse(recv)
        text = (f"for __si in range(len({xs}) - 1, 0, -1):\n    __sj = {r}.randbelow(__si + 1)\n"
                f"    {xs}[__si], {xs}[__sj] = {xs}[__sj], {xs}[__si]\n")
        st = ast.parse(text).body[0]
        for sub in ast.walk(st):
            if hasattr(sub, "lineno"):
                sub.lineno = v.lineno
        return self.stmt(st)

    # ---------- sys.stdin / sys.stdout ----------
    def stdio_call(self, node, stream, m):
        a = node.args
        if stream == "stdin":
            if m == "read" and not a:
                return ir.Call("stdin_read", [], STR, "builtin")
            if m == "readline" and not a:
                return ir.Call("stdin_readline", [], STR, "builtin")
            if m == "readlines" and not a:
                return ir.Call("stdin_readlines", [], list_of(STR), "builtin")
        else:
            err = stream == "stderr"
            if m == "write" and len(a) == 1 and not node.keywords:
                s = self.coerce(self.expr(a[0]), STR, node)
                return ir.Call("stderr_write" if err else "stdout_write", [s], NONE, "builtin")
            if m == "flush" and not a:
                return ir.Call("stdout_flush", [], NONE, "builtin")
        raise Unsupported(f"sys.{stream}.{m}() non supporté", node)

    # ---------- dict.fromkeys ----------
    def dict_fromkeys(self, node):
        if node.keywords or len(node.args) != 2:
            raise Unsupported("dict.fromkeys(clés, valeur) : la valeur est obligatoire", node)
        k = f"__fk{self.tmp}"
        self.tmp += 1
        comp = ast.DictComp(key=ast.Name(id=k, ctx=ast.Load()), value=node.args[1],
                            generators=[ast.comprehension(target=ast.Name(id=k, ctx=ast.Store()), iter=node.args[0], ifs=[], is_async=0)])
        return self.expr(ast.copy_location(ast.fix_missing_locations(comp), node))

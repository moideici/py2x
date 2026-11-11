"""Émetteur C++ (C++20). int -> long long, float -> double, str -> std::string, list -> PyList, dict -> PyDict (poignées partagées)."""
import re

from . import ir
from .names import CPP_RESERVED, func_name, mangle
from .types import BOOL, FLOAT, INT, NONE, STR, is_container

from .lib import CONSTS, LIB, LOG  # noqa: E402
from .runtime_cpp import PRELUDE as _CORE  # noqa: E402
from .runtime_cpp_fmt import FORMAT  # noqa: E402
from .runtime_cpp_coll import COLLECTIONS  # noqa: E402
from .runtime_cpp_exc import EXC_CPP  # noqa: E402
from .runtime_cpp_str import STRINGS  # noqa: E402

PRELUDE = _CORE.replace("// --- fin du runtime ---", STRINGS + FORMAT + COLLECTIONS + EXC_CPP + "// --- fin du runtime ---")

CMP = {"==": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
FLOAT_CASTS = {(INT, FLOAT), (BOOL, FLOAT)}


def cstr(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif o < 32 or o == 127:
            out.append("\\%03o" % o)
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


SCALARS = (INT, FLOAT, BOOL, STR)


class CppEmitter:
    def __init__(self):
        self.lines = []
        self.ind = 0
        self.n = 0
        self.in_ctor = False
        self.classes_by_name = {}
        self.cur_owner = None

    def emit(self, module):
        out = [PRELUDE]
        funcs, classes = module.funcs, module.classes
        self.classes_by_name = {c.name: c for c in classes}
        for c in classes:
            out.append(f"struct {self.cname(c.name)};")
        for c in classes:
            out.append(self.class_decl(c))
        for c in classes:
            out.append(self.print_decls(c))
        for n, t in module.globals:  # variables de module : définies ici, affectées dans main() dans l'ordre du source
            out.append(f"{self.ty(t)} {self.var(n)}{{}};")
        for f in funcs:
            out.append(self.signature(f) + ";")
        out.append("")
        for c in classes:
            out.append(self.print_defs(c))
        for c in classes:
            out.append(self.class_defs(c))
        for f in funcs:
            out.append(self.func(f))
        if module.entry is not None:
            out.append(self.func(module.entry, entry=True))
        return "\n".join(out) + "\n"

    # ---------- classes ----------
    def cname(self, name):
        return mangle(name, CPP_RESERVED)

    def mname(self, name):
        if name.startswith("__") and name.endswith("__") and name not in ("__str__", "__repr__", "__init__"):
            return "py_op_" + name[2:-2]  # __len__ -> py_op_len (les noms avec __ sont réservés en C++)
        return {"__str__": "py_str_m", "__repr__": "py_repr_m"}.get(name) or mangle(name, CPP_RESERVED)

    def class_decl(self, c):
        n = self.cname(c.name)
        if c.hier and not c.is_dataclass:
            return self.class_decl_hier(c)
        L = [f"struct {n} : std::enable_shared_from_this<{n}> {{",
             f"    static constexpr bool py_value_eq = {'true' if c.is_dataclass else 'false'};",
             f"    static constexpr bool py_has_eq = {'true' if c.has_eq else 'false'};",
             f"    static constexpr bool py_has_lt = {'true' if c.has_lt else 'false'};"]
        for fname, ft, _ in c.fields:
            L.append(f"    {self.ty(ft)} {self.var(fname)}{{}};")
        if c.is_dataclass and c.fields:
            ps = ", ".join(f"{self.ty(ft)} {self.var(fn)}_" for fn, ft, _ in c.fields)
            inits = ", ".join(f"{self.var(fn)}({self.var(fn)}_)" for fn, _, _ in c.fields)
            L.append(f"    {n}({ps}) : {inits} {{ {'py_op_post_init(); ' if c.has_post_init else ''}}}")
        elif c.is_dataclass:
            L.append(f"    {n}() {{}}")
        elif c.init is not None:
            L.append(f"    {n}({self.params(c.init)});")
        for m in c.methods:
            L.append(f"    {self.ty(m.ret)} {self.mname(m.name)}({self.params(m)});")
        if c.is_dataclass:
            L.append(f"    bool py_eq_fields(const {n}& o) const;")
        L.append("};")
        return "\n".join(L)

    def class_decl_hier(self, c):
        """Classe d'une hiérarchie : méthodes virtuelles ; __init__ devient une méthode py_init_<Classe> appelée par le constructeur
        (Python exécute super().__init__() comme une instruction ordinaire, pas comme une liste d'initialisation)."""
        n = self.cname(c.name)
        if c.base is None:
            L = [f"struct {n} : std::enable_shared_from_this<{n}> {{"]
        else:
            L = [f"struct {n} : {self.cname(c.base)} {{"]
        L.append("    static constexpr bool py_value_eq = false;")
        L.append(f"    static constexpr bool py_has_eq = {'true' if c.has_eq else 'false'};")
        L.append(f"    static constexpr bool py_has_lt = {'true' if c.has_lt else 'false'};")
        for fname, ft, _ in c.fields:
            L.append(f"    {self.ty(ft)} {self.var(fname)}{{}};")
        if c.init is not None:
            ps = self.params(c.init)
            names = ", ".join(self.var(p) for p, _ in c.init.params)
            setargs = f"this->py_set_args({names}); " if c.is_exc else ""
            L.append(f"    {n}() = default;")
            L.append(f"    {n}({ps}) {{ {setargs}py_init_{n}({names}); }}")
            L.append(f"    void py_init_{n}({ps});")
        elif c.base is not None:
            L.append(f"    using {self.cname(c.base)}::{self.cname(c.base)};")
        if c.base is None:
            L.append(f"    virtual ~{n}() = default;")
        if c.is_exc or c.base is not None:
            L.append(f'    const char* py_name() const override {{ return "{c.name}"; }}')
        else:
            L.append(f'    virtual const char* py_name() const {{ return "{c.name}"; }}')
        for m in c.methods:
            tail = " override" if m.name in c.overrides else ""
            head = "" if m.name in c.overrides else "virtual "
            L.append(f"    {head}{self.ty(m.ret)} {self.mname(m.name)}({self.params(m)}){tail};")
        L.append("};")
        return "\n".join(L)

    def repr_expr(self, c):
        if c.has_repr:
            return "p->py_repr_m()"
        e = f'std::string("{c.name}(")'  # repr généré d'une dataclass : Point(x=1, y=2)
        for i, (fn, _, _) in enumerate(c.fields):
            e += f' + "{"" if i == 0 else ", "}{fn}=" + py_repr(p->{self.var(fn)})'
        return e + ' + ")"'

    def has_printing(self, c):
        return c.is_dataclass or c.has_repr or c.has_str or c.is_exc

    def print_decls(self, c):
        if not self.has_printing(c):
            return ""
        n = self.cname(c.name)
        return (f"static inline std::string py_repr(const std::shared_ptr<{n}>& p);\n"
                f"static inline std::string py_str(const std::shared_ptr<{n}>& p);")

    def print_defs(self, c):
        if not self.has_printing(c):
            return ""
        n = self.cname(c.name)
        repr_ = self.repr_expr(c) if (c.is_dataclass or c.has_repr) else '"<object>"'
        str_ = "p->py_str_m()" if c.has_str else "py_repr(p)"
        if c.is_exc:
            repr_ = "p->py_repr_m()" if c.has_repr else "p->py_exc_repr()"
            str_ = "p->py_str_m()" if c.has_str else "p->py_exc_str()"
        return (f"static inline std::string py_repr(const std::shared_ptr<{n}>& p) {{ if (!p) return \"None\"; return {repr_}; }}\n"
                f"static inline std::string py_str(const std::shared_ptr<{n}>& p) {{ if (!p) return \"None\"; return {str_}; }}")

    def class_defs(self, c):
        n = self.cname(c.name)
        out = []
        self.cur_owner = c
        if c.init is not None:
            out.append(self.func(c.init))
        for m in c.methods:
            out.append(self.func(m))
        self.cur_owner = None
        if c.is_dataclass:
            body = " && ".join(f"py_eq({self.var(fn)}, o.{self.var(fn)})" for fn, _, _ in c.fields if fn not in c.nocompare) or "true"
            out.append(f"bool {n}::py_eq_fields(const {n}& o) const {{ return {body}; }}\n")
        return "\n".join(out)

    # ---------- types et noms ----------
    def ty(self, t):
        if t == INT:
            return "long long"
        if t == FLOAT:
            return "double"
        if t == BOOL:
            return "bool"
        if t == STR:
            return "std::string"
        if t == NONE:
            return "void"
        if t.kind == "list":
            return f"PyList<{self.ty(t.args[0])}>"
        if t.kind == "gen":
            return f"PyGen<{self.ty(t.args[0])}>"
        if t.kind == "func":
            return f"std::function<{self.ty(t.args[0])}({', '.join(self.ty(a) for a in t.args[1:])})>"
        if t.kind == "vtuple":
            return f"PyVT<{self.ty(t.args[0])}>"
        if t.kind == "set":
            return f"PySet<{self.ty(t.args[0])}>"
        if t.kind == "deque":
            return f"PyDeque<{self.ty(t.args[0])}>"
        if t.kind == "tuple":
            return f"std::tuple<{', '.join(self.ty(a) for a in t.args)}>"
        if t.kind == "class":
            return f"std::shared_ptr<{self.cname(t.args[0])}>"
        if t.kind == "optional":  # un objet est nullable en soi (shared_ptr nul) ; les autres types passent par std::optional
            inner = t.args[0]
            return self.ty(inner) if inner.kind == "class" else f"std::optional<{self.ty(inner)}>"
        return f"PyDict<{self.ty(t.args[0])}, {self.ty(t.args[1])}>"

    def var(self, name):
        return mangle(name, CPP_RESERVED)

    def params(self, f):
        # list/dict/objets = poignées (alias à la copie, comme les références Python) ; str immuable : référence const
        if f.is_gen:  # une coroutine copie ses paramètres dans son cadre : pas de référence (elle survivrait à l'appelant)
            return ", ".join(f"{self.ty(t)} {self.var(n)}" for n, t in f.params)
        return ", ".join((f"const {self.ty(t)}& {self.var(n)}" if t == STR and n not in f.reassigned else f"{self.ty(t)} {self.var(n)}")
                         for n, t in f.params)

    def signature(self, f):
        return f"{self.ty(f.ret)} {func_name(f.name, CPP_RESERVED)}({self.params(f)})"

    # ---------- fonctions ----------
    def func(self, f, entry=False):
        self.lines, self.ind = [], 1
        self.in_gen = f.is_gen
        self.in_ctor = bool(f.owner) and f.name == "__init__"
        if entry:
            head = "int main()"
        elif self.in_ctor and self.cur_owner is not None and self.cur_owner.hier:
            n = self.cname(f.owner)
            head = f"void {n}::py_init_{n}({self.params(f)})"
        elif self.in_ctor:
            n = self.cname(f.owner)
            head = f"{n}::{n}({self.params(f)})"
        elif f.owner:
            head = f"{self.ty(f.ret)} {self.cname(f.owner)}::{self.mname(f.name)}({self.params(f)})"
        else:
            head = self.signature(f)
        for name, t in f.hoisted:
            self.w(f"{self.ty(t)} {self.var(name)}{{}};")
        self.stmts(f.body)
        if entry:
            self.w("return 0;")
            self.lines = (["    try {"] + ["    " + ln for ln in self.lines]
                          + ["    } catch (const PyThrow& __e) {",
                             "        std::cout.flush();",
                             '        std::cerr << "Traceback (most recent call last):\\n" << __e.p->py_name() << ": " << __e.p->py_exc_str() << "\\n";',
                             "        return 1;", "    }"])
        body = "\n".join(self.lines)
        if f.owner and not self.in_ctor and re.search(r"\bself\b", body):
            # self utilisé comme VALEUR (return self, f(self)...) : il faut un shared_ptr, pas le this brut
            body = f"    auto self = std::static_pointer_cast<{self.cname(f.owner)}>(shared_from_this());\n" + body
        self.in_ctor = False
        return head + " {\n" + body + "\n}\n"

    def w(self, s):
        self.lines.append("    " * self.ind + s)

    def stmts(self, body):
        for s in body:
            getattr(self, "s_" + type(s).__name__)(s)

    def block(self, body):
        self.ind += 1
        self.stmts(body)
        self.ind -= 1

    # ---------- instructions ----------
    def s_VarDecl(self, s):
        if s.init is None:
            self.w(f"{self.ty(s.type)} {self.var(s.name)}{{}};")
        else:
            self.w(f"{self.ty(s.type)} {self.var(s.name)} = {self.x(s.init)};")

    def s_Assign(self, s):
        self.w(f"{self.lvalue(s.target)} = {self.x(s.value)};")

    def s_If(self, s, elif_=False):
        self.w(("} else if (" if elif_ else "if (") + self.x(s.cond) + ") {")
        self.block(s.body)
        orelse = s.orelse
        while orelse:
            if len(orelse) == 1 and isinstance(orelse[0], ir.If):
                self.s_If(orelse[0], elif_=True)
                return
            self.w("} else {")
            self.block(orelse)
            break
        self.w("}")

    def s_While(self, s):
        self.w(f"while ({self.x(s.cond)}) {{")
        self.block(s.body)
        self.w("}")

    def s_ForRange(self, s):
        v, end = self.var(s.var), f"__end{self.n}"
        if not isinstance(s.step, int):  # pas calculé à l'exécution : le test dépend du signe du pas
            st = f"__step{self.n}"
            self.n += 1
            self.w(f"for (long long {v} = {self.x(s.start)}, {end} = {self.x(s.stop)}, {st} = py_range_step({self.x(s.step)}); "
                   f"({st} > 0 ? {v} < {end} : {v} > {end}); {v} += {st}) {{")
            self.block(s.body)
            self.w("}")
            return
        self.n += 1
        cmp_ = "<" if s.step > 0 else ">"
        self.w(f"for (long long {v} = {self.x(s.start)}, {end} = {self.x(s.stop)}; {v} {cmp_} {end}; {v} += {s.step}LL) {{")
        self.block(s.body)
        self.w("}")

    def s_ForEach(self, s):
        v = self.var(s.var)
        if s.iterable.type.kind == "dict":
            kv = f"__kv{self.n}"
            self.n += 1
            self.w(f"for (const auto& {kv} : {self.x(s.iterable)}) {{")
            self.ind += 1
            self.w(f"{self.ty(s.elem_type)} {v} = {kv}.first;")
            self.ind -= 1
        else:
            self.w(f"for (auto {v} : {self.x(s.iterable)}) {{")  # poignées : copier = alias, comme la variable de boucle Python
        self.block(s.body)
        self.w("}")

    def bounds(self, lo, hi, step):
        l = ("0LL", "false") if lo is None else (self.x(lo), "true")
        h = ("0LL", "false") if hi is None else (self.x(hi), "true")
        return f"{l[0]}, {l[1]}, {h[0]}, {h[1]}, {self.x(step) if step is not None else '1LL'}"

    def s_SliceAssign(self, s):
        self.w(f"py_setslice({self.x(s.base)}, {self.bounds(s.lo, s.hi, s.step)}, {self.x(s.value)});")

    def s_Delete(self, s):
        b = self.x(s.base)
        if s.kind == "key":
            self.w(f"{b}.erase({self.x(s.args[0])});")
        elif s.kind == "item":
            self.w(f"py_delitem({b}, {self.x(s.args[0])});")
        else:
            self.w(f"py_delslice({b}, {self.bounds(*s.args)});")

    def s_LocalFunc(self, s):
        f = s.func
        sig = ", ".join(self.ty(t) for _, t in f.params)
        cap = "[=]" if s.escapes else "[&]"  # une fonction qui sert de valeur survit à son environnement : capture par copie
        mut = " mutable" if s.escapes else ""
        self.w(f"std::function<{self.ty(f.ret)}({sig})> {self.var(f.name)} = {cap}({self.params(f)}){mut} -> {self.ty(f.ret)} {{")
        self.ind += 1
        for name, t in f.hoisted:
            self.w(f"{self.ty(t)} {self.var(name)}{{}};")
        self.stmts(f.body)
        self.ind -= 1
        self.w("};")

    def s_Raise(self, s):
        self.w("throw;" if s.value is None else f"py_raise({self.x(s.value)});")

    def s_Try(self, s):
        k = self.n
        self.n += 1
        self.w("{")
        self.ind += 1
        if s.final:
            self.w(f"PyFinally __fin{k}([&]() {{")
            self.block(s.final)
            self.w("});")
        if s.orelse:
            self.w(f"bool __ok{k} = false;")
        if s.handlers:
            self.w("try {")
            self.block(s.body)
            if s.orelse:
                self.w(f"    __ok{k} = true;")
            self.w(f"}} catch (const PyThrow& __ex{k}) {{")
            self.ind += 1
            first = True
            for h in s.handlers:
                if h.classes is None:
                    self.w("{" if first else "else {")
                else:
                    cond = " || ".join(f"py_isinst<{self.cname(c)}>(__ex{k})" for c in h.classes)
                    self.w(("if (" if first else "else if (") + cond + ") {")
                first = False
                self.ind += 1
                if h.var:
                    self.w(f"auto {self.var(h.var)} = std::static_pointer_cast<{self.cname(h.vtype.args[0])}>(__ex{k}.p);")
                self.ind -= 1
                self.block(h.body)
                self.w("}")
            if all(h.classes is not None for h in s.handlers):
                self.w("else { throw; }")
            self.ind -= 1
            self.w("}")
        else:
            self.stmts(s.body)
        if s.orelse:
            self.w(f"if (__ok{k}) {{")
            self.block(s.orelse)
            self.w("}")
        self.ind -= 1
        self.w("}")

    def s_Return(self, s):
        if getattr(self, "in_gen", False):
            self.w("co_return;")
            return
        self.w("return;" if s.value is None else f"return {self.x(s.value)};")

    def s_Yield(self, s):
        self.w(f"co_yield {self.x(s.value)};")

    def s_Break(self, s):
        self.w("break;")

    def s_Continue(self, s):
        self.w("continue;")

    def s_ExprStmt(self, s):
        self.w(self.x(s.expr) + ";")

    def s_Print(self, s):
        out = "std::cerr" if s.err else "std::cout"
        sep = self.x(s.sep) if s.sep is not None else '" "'
        end = self.x(s.end) if s.end is not None else '"\\n"'
        if len(s.args) > 1 and any(not isinstance(a, (ir.Var, ir.Const)) for a in s.args[1:]):
            # Python évalue TOUS les arguments avant d'en convertir un en texte : print(d, d.pop()) affiche d déjà modifié
            self.w("{")
            self.ind += 1
            names = []
            for a in s.args:
                nm = f"__p{self.n}"
                self.n += 1
                names.append(nm)
                self.w(f"auto {nm} = {self.x(a)};")
            parts = f" << {sep} << ".join(f"py_str({nm})" for nm in names)
            self.w(f"{out} << {parts} << {end};")
            self.ind -= 1
            self.w("}")
            return
        parts = f" << {sep} << ".join(f"py_str({self.x(a)})" for a in s.args)
        self.w(f"{out} << {parts + ' << ' if parts else ''}{end};")

    # ---------- expressions ----------
    def lvalue(self, t):
        if isinstance(t, ir.Var):
            return self.var(t.name)
        if isinstance(t, ir.Attr):
            return self.x_Attr(t)
        if t.base.type.kind == "dict":
            return f"{self.x(t.base)}[{self.x(t.index)}]"
        return f"py_at({self.x(t.base)}, {self.x(t.index)})"

    def x(self, e):
        return getattr(self, "x_" + type(e).__name__)(e)

    def x_Const(self, e):
        if e.type == INT:
            return f"{e.value}LL"
        if e.type == FLOAT:
            r = repr(e.value)
            return r if any(c in r for c in ".eE") else r + ".0"
        if e.type == BOOL:
            return "true" if e.value else "false"
        if e.type == NONE:
            return 'std::string("None")'
        return f"std::string({cstr(e.value)})"

    def x_Var(self, e):
        if e.name == "self":
            return "this" if self.in_ctor else "self"  # `self` valeur = shared_ptr obtenu par shared_from_this() (voir func)
        return self.var(e.name)

    def obj(self, base):
        """Base d'un accès -> : `this` pour self (évite shared_from_this, interdit dans un constructeur)."""
        if isinstance(base, ir.Var) and base.name == "self":
            return "this"
        return self.x(base)

    def x_Attr(self, e):
        return f"{self.obj(e.obj)}->{self.var(e.name)}"

    def x_New(self, e):
        return f"std::make_shared<{self.cname(e.cls)}>({', '.join(self.x(a) for a in e.args)})"

    def x_UserMethodCall(self, e):
        return f"{self.obj(e.obj)}->{self.mname(e.name)}({', '.join(self.x(a) for a in e.args)})"

    def x_Comp(self, e):
        """Compréhension -> lambda immédiatement appelée, dont le corps réutilise les émetteurs d'instructions."""
        saved = (self.lines, self.ind)
        self.lines, self.ind = [], saved[1] + 1
        self.w(f"{self.ty(e.type)} {self.var(e.result)}{{}};")
        self.stmts(e.body)
        self.w(f"return {self.var(e.result)};")
        inner = "\n".join(self.lines)
        self.lines, self.ind = saved
        return "[&]() {\n" + inner + "\n" + "    " * saved[1] + "}()"

    def x_BinOp(self, e):
        l, r = self.x(e.left), self.x(e.right)
        if e.type.kind == "list":
            return f"py_concat({l}, {r})" if e.op == "+" else f"py_repeat({l}, {r})"
        if e.op == "*" and e.type == STR:
            return f"py_repeat_str({l}, {r})"
        if e.op in ("/", "/i"):
            return f"py_div({l}, {r})" if e.op == "/i" else f"py_fdiv({l}, {r})"
        if e.type == INT and e.op in ("+", "-", "*", "<<", ">>"):  # arithmétique 64 bits vérifiée : dépassement -> OverflowError
            return f"py_{ {'+': 'add', '-': 'sub', '*': 'mul', '<<': 'shl', '>>': 'shr'}[e.op] }({l}, {r})"
        if e.op == "//":
            return f"py_floordiv({l}, {r})"
        if e.op == "%":
            return f"py_mod({l}, {r})"
        if e.op == "**":
            return f"py_pow({l}, {r})" if e.type == INT else f"py_fpow({l}, {r})"
        return f"({l} {e.op} {r})"

    def x_Cmp(self, e):
        l, r = self.x(e.left), self.x(e.right)
        if e.op in ("in", "notin"):
            if e.right.type == STR:
                s = f"({r}.find({l}) != std::string::npos)"
            else:
                s = f"py_in({r}, {l})"
            return s if e.op == "in" else f"(!{s})"
        if e.op in ("is", "isnot"):
            return f"({l} {'==' if e.op == 'is' else '!='} {r})"
        if e.op in ("==", "!=") and e.left.type not in SCALARS:  # list/dict/tuple/objets : égalité à la Python
            return f"py_eq({l}, {r})" if e.op == "==" else f"(!py_eq({l}, {r}))"
        return f"({l} {CMP[e.op]} {r})"

    def x_BoolOp(self, e):
        sym = " && " if e.op == "and" else " || "
        return "(" + sym.join(self.x(v) for v in e.values) + ")"

    def x_Unary(self, e):
        if e.op == "-" and e.type == INT:
            return f"py_neg({self.x(e.operand)})"
        return f"({'!' if e.op == 'not' else e.op}{self.x(e.operand)})"

    def x_Ternary(self, e):
        return f"({self.x(e.cond)} ? {self.x(e.a)} : {self.x(e.b)})"

    def x_Cast(self, e):
        if e.operand.type == FLOAT and e.type == INT:
            return f"py_f2i({self.x(e.operand)})"
        return f"(({self.ty(e.type)})({self.x(e.operand)}))"

    def x_Index(self, e):
        b, i = self.x(e.base), self.x(e.index)
        if e.base.type.kind == "dict":
            return f"{b}.at({i})"
        if e.base.type == STR:
            return f"std::string(1, py_at({b}, {i}))"
        return f"py_at({b}, {i})"

    def x_ListLit(self, e):
        et = self.ty(e.type.args[0])
        return f"{self.ty(e.type)}(std::vector<{et}>{{{', '.join(self.x(v) for v in e.elems)}}})"

    def x_DictLit(self, e):
        items = ", ".join(f"{{{self.x(k)}, {self.x(v)}}}" for k, v in zip(e.keys, e.values))
        return f"{self.ty(e.type)}{{{items}}}"

    def x_KeyOp(self, e):
        lam = e.lam
        fn = f"[&](const {self.ty(lam.ptype)}& {self.var(lam.param)}) {{ return {self.x(lam.body)}; }}"
        xs = self.x(e.args[0])
        if e.kind in ("min", "max"):
            return f"py_{e.kind}_key({xs}, {fn})"
        return f"py_{e.kind}_key({xs}, {fn}, {self.x(e.rev)})"

    def x_LambdaVal(self, e):
        ps = ", ".join(f"{self.ty(t)} {self.var(n)}" for n, t in e.params)
        ret = self.ty(e.type.args[0])
        if e.type.args[0] == NONE:
            return f"[=]({ps}) {{ {self.x(e.body)}; }}"
        return f"[=]({ps}) -> {ret} {{ return {self.x(e.body)}; }}"

    def x_FuncRef(self, e):
        return self.var(e.name) if e.kind == "local" else func_name(e.name, CPP_RESERVED)

    def x_CallVal(self, e):
        return f"{self.x(e.fn)}({', '.join(self.x(a) for a in e.args)})"

    def x_SuperCall(self, e):
        a = ", ".join(self.x(v) for v in e.args)
        if e.name == "__init__":
            if e.owner is None:
                return f"this->py_set_args({a})" if self.cur_owner is not None and self.cur_owner.is_exc else "((void)0)"
            return f"{self.cname(e.owner)}::py_init_{self.cname(e.owner)}({a})"
        return f"{self.cname(e.owner)}::{self.mname(e.name)}({a})"

    def x_IsInstance(self, e):
        x = self.x(e.operand)
        return "(" + " || ".join(f"std::dynamic_pointer_cast<{self.cname(c)}>({x}) != nullptr" for c in e.classes) + ")"

    def x_Downcast(self, e):
        return f"std::static_pointer_cast<{self.cname(e.type.args[0])}>({self.x(e.operand)})"

    def x_DictNew(self, e):
        return f'py_dnew<{self.ty(e.type.args[0])}, {self.ty(e.type.args[1])}>({e.mode}, {cstr(e.factory)})'

    def x_NoneOf(self, e):
        return f"{self.ty(e.type)}()"

    def x_Wrap(self, e):
        return self.x(e.operand) if e.type.args[0].kind == "class" else f"{self.ty(e.type)}({self.x(e.operand)})"

    def x_Unwrap(self, e):
        return f"py_nn({self.x(e.operand)})" if e.type.kind == "class" else f"py_val({self.x(e.operand)})"

    def x_IsNone(self, e):
        inner = e.operand.type.args[0]
        if inner.kind == "class":
            return f"({self.x(e.operand)} {'!=' if e.negate else '=='} nullptr)"
        return f"({'' if e.negate else '!'}{self.x(e.operand)}.has_value())"

    def x_Slice(self, e):
        return f"py_slice({self.x(e.base)}, {self.bounds(e.lo, e.hi, e.step)})"

    def x_LibConst(self, e):
        return CONSTS[e.name][2]

    def x_TupleLit(self, e):
        return f"{self.ty(e.type)}({', '.join(self.x(v) for v in e.elems)})"

    def x_TupleGet(self, e):
        return f"std::get<{e.index}>({self.x(e.base)})"

    def x_MethodCall(self, e):
        o = self.x(e.obj)
        if e.name in ("keys", "values", "items"):
            return f"py_{e.name}({o})"
        if e.name == "get1":
            vt = e.obj.type.args[1]
            if vt.kind in ("class", "optional"):  # valeur nullable en soi : défaut = valeur vide
                return f"py_get({o}, {self.x(e.args[0])}, {self.ty(vt)}())"
            return f"py_get1({o}, {self.x(e.args[0])})"
        if e.name in ("pop", "extend", "insert", "count", "index", "remove", "setdefault", "update", "popitem", "copy", "clear"):
            name = e.name
            if e.obj.type.kind == "dict":
                name = {"pop": "dpop", "update": "dupdate", "copy": "dcopy", "clear": "dclear"}.get(name, name)
            elif name == "clear":
                name = "lclear"
            return f"py_{name}({', '.join([o] + [self.x(a) for a in e.args])})"
        if e.name == "append":
            return f"{o}.push_back({self.x(e.args[0])})"
        if e.name == "sort":
            return f"std::sort({o}.begin(), {o}.end())"
        if e.name == "reverse":
            return f"std::reverse({o}.begin(), {o}.end())"
        return f"py_get({o}, {self.x(e.args[0])}, {self.x(e.args[1])})"  # get

    def x_Call(self, e):
        a = [self.x(v) for v in e.args]
        if e.kind == "local":
            return f"{self.var(e.name)}({', '.join(a)})"
        if e.kind == "user":
            return f"{func_name(e.name, CPP_RESERVED)}({', '.join(a)})"
        if e.kind == "lib":
            tpl = LOG[len(a)][0] if e.name == "math.log" else LIB[e.name].cpp
            return tpl.format(*a)
        n = e.name
        if n == "vt_list":
            return f"py_vt_list({a[0]})"
        if n == "list" and e.type.kind == "vtuple":
            return f"{self.ty(e.type)}(py_list({a[0]}))"
        if n == "vt_to_tuples":
            return f"py_vt_to_tuples<{len(e.type.args[0].args)}>({a[0]})"
        if n in ("product2", "product3"):
            return f"py_{n}({', '.join(a)})"
        if n == "join_star":
            return f"py_join_star({a[0]}, {a[1]})"
        if n == "range_list":
            return f"py_range_list({', '.join(a)})"
        if n == "type_name":
            c = self.classes_by_name.get(e.args[0].type.args[0])
            if c is not None and not c.hier:
                return f"std::string({cstr(c.name)})"
            return f"std::string({a[0]}->py_name())"
        if n == "set_new":
            return f"{self.ty(e.type)}()"
        if n == "deque_new":
            return f"{self.ty(e.type)}({a[0]})"
        if n == "len":
            return f"((long long){a[0]}.size())"
        if n == "abs":
            return f"py_iabs({a[0]})" if e.type == INT else f"std::fabs({a[0]})"
        if n == "str":
            return f"py_str({a[0]})"
        if n in ("enumerate", "zip"):
            return f"py_{n}({', '.join(a)})"
        if n in ("min", "max"):
            t = self.ty(e.type)
            r = a[-1]
            for v in reversed(a[:-1]):
                r = f"std::{n}<{t}>({v}, {r})"
            return r
        return f"py_{n}({', '.join(a)})"  # min_list max_list sum sorted sum_start round ... (tous les arguments)

"""Frontend : héritage, super(), isinstance, exceptions (raise / try / except / finally / assert)."""
import ast

from . import ir
from .errors import Unsupported
from .types import BOOL, FLOAT, INT, NONE, STR, class_of


class ClassesMixin:
    # ---------- appel de super() ----------
    def is_super_call(self, f):
        return (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Call) and isinstance(f.value.func, ast.Name)
                and f.value.func.id == "super" and not f.value.args and not f.value.keywords)

    def super_call(self, node):
        if self.cls is None:
            raise Unsupported("super() hors d'une méthode", node)
        m = node.func.attr
        cinfo = self.fe.classes[self.cls]
        if cinfo.base is None:
            raise Unsupported("super() dans une classe sans classe parente", node)
        if m == "__init__":
            if not self.in_init:
                raise Unsupported("super().__init__() en dehors de __init__", node)
            eff = self.fe.effective_init(cinfo.base)
            if eff is None:
                if cinfo.is_exc:  # Exception.__init__(*args) : fixe args
                    if node.keywords:
                        raise Unsupported("super().__init__ d'une exception : arguments positionnels seulement", node)
                    return ir.SuperCall(None, "__init__", [self.unopt(self.expr(a)) for a in node.args], NONE)
                if node.args or node.keywords:
                    raise Unsupported("super().__init__(...) : la classe parente n'a pas de __init__", node)
                return ir.SuperCall(None, "__init__", [], NONE)
            owner, (params, _, defaults) = eff
            args = self.bind_args(node, params, defaults, f"{owner.name}.__init__()", callee=f"{owner.name}.__init__")
            return ir.SuperCall(owner.name, "__init__", args, NONE)
        found = self.fe.lookup_method(cinfo.base, m)
        if found is None:
            raise Unsupported(f"super().{m}() : méthode inconnue dans les classes parentes", node)
        owner, (params, ret, defaults) = found
        args = self.bind_args(node, params, defaults, f"{owner.name}.{m}()", callee=f"{owner.name}.{m}")
        return ir.SuperCall(owner.name, m, args, ret)

    # ---------- isinstance ----------
    BUILTIN_TYPES = {"int": INT, "float": FLOAT, "str": STR, "bool": BOOL}

    def b_isinstance(self, node):
        if len(node.args) != 2 or node.keywords:
            raise Unsupported("isinstance(x, classe) attend 2 arguments", node)
        x = self.expr(node.args[0])
        spec = node.args[1]
        elts = spec.elts if isinstance(spec, ast.Tuple) else [spec]
        names, builtins = [], []
        for el in elts:
            if isinstance(el, ast.Name) and el.id in self.fe.classes and el.id not in self.scope:
                names.append(el.id)
            elif isinstance(el, ast.Name) and el.id in self.BUILTIN_TYPES:
                builtins.append(self.BUILTIN_TYPES[el.id])
            else:
                raise Unsupported(f"isinstance : classe non supportée ({ast.unparse(el)})", node)
        xt = x.type.args[0] if x.type.kind == "optional" else x.type
        if xt.kind != "class":
            if not self.is_pure(x):
                raise Unsupported("isinstance sur une expression non simple dont le type est statique", node)
            return ir.Const(xt in builtins or (xt == BOOL and INT in builtins), BOOL)
        static = xt.args[0]
        if x.type.kind != "optional" and any(self.fe.is_subclass(static, n) for n in names):
            if not self.is_pure(x):
                raise Unsupported("isinstance sur une expression non simple dont le type est statique", node)
            return ir.Const(True, BOOL)
        if not any(self.fe.is_subclass(n, static) or self.fe.is_subclass(static, n) for n in names):
            if not self.is_pure(x):
                raise Unsupported("isinstance sur une expression non simple dont le type est statique", node)
            return ir.Const(False, BOOL)
        return ir.IsInstance(x, names)

    # ---------- raise / try / assert ----------
    def exc_class(self, node, what):
        if isinstance(node, ast.Name) and node.id in self.fe.classes and node.id not in self.scope and self.fe.classes[node.id].is_exc:
            return node.id
        raise Unsupported(f"{what} : classe d'exception attendue (ValueError, une sous-classe d'Exception...)", node)

    def s_Raise(self, node):
        if node.exc is None:
            if self.handler_depth == 0:
                raise Unsupported("`raise` seul en dehors d'un bloc except", node)
            return [ir.Raise(None)]
        e = node.exc
        if isinstance(e, ast.Name) and e.id in self.fe.classes and e.id not in self.scope:
            self.exc_class(e, "raise")
            v = self.construct(e.id, ast.copy_location(ast.Call(func=e, args=[], keywords=[]), node))
        else:
            v = self.unopt(self.expr(e))
        if v.type.kind != "class" or not self.fe.classes[v.type.args[0]].is_exc:
            raise Unsupported(f"raise : on ne peut lever qu'une exception (type {v.type})", node)
        return [ir.Raise(v)]

    def s_Assert(self, node):
        c = self.cond(node.test)
        args = [self.unopt(self.expr(node.msg))] if node.msg is not None else []
        raise_ = ir.Raise(ir.New("AssertionError", args, class_of("AssertionError")))
        return [ir.If(ir.Unary("not", c, BOOL), [raise_], [])]

    def except_types(self, t, node):
        if t is None:
            return None, class_of("Exception")
        elts = t.elts if isinstance(t, ast.Tuple) else [t]
        names = [self.exc_class(el, "except") for el in elts]
        lub = self.fe.lub_class(names) if len(names) > 1 else names[0]
        return names, class_of(lub)

    @staticmethod
    def exits_in_finally(nodes):
        return any(isinstance(n, (ast.Return, ast.Break, ast.Continue)) for st in nodes for n in ast.walk(st))

    def s_Try(self, node):
        if not node.handlers and not node.finalbody:
            raise Unsupported("try sans except ni finally", node)
        if node.finalbody and self.exits_in_finally(node.finalbody):
            raise Unsupported("return/break/continue dans un bloc finally non supportés", node)
        body = self.block(node.body)
        handlers = []
        for h in node.handlers:
            classes, htype = self.except_types(h.type, h)
            bound = []
            if h.name:
                if h.name in self.scope or h.name in self.loopvars:
                    raise Unsupported(f"`except ... as {h.name}` : le nom est déjà utilisé comme variable dans cette fonction", h)
                self.bind_local(h.name, htype, bound)
            self.handler_depth += 1
            try:
                hb = self.block(h.body)
            finally:
                self.handler_depth -= 1
                self.unbind(bound)
            handlers.append(ir.Handler(classes, h.name, htype, hb))
        orelse = self.block(node.orelse) if node.orelse else []
        final = self.block(node.finalbody) if node.finalbody else []
        return [ir.Try(body, handlers, orelse, final)]

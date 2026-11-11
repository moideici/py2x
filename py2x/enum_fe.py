"""Frontend : Enum et variables de classe, ramenés à des globales de module + une classe ordinaire.

class Couleur(Enum): ROUGE = 1  ->  classe (name, value) + globale Couleur_ROUGE = Couleur("ROUGE", 1) + fonction Couleur_from_value(v)
class A: n = 0                  ->  globale A_n = 0 ; A.n, self.n (lecture) et A.n += 1 y accèdent."""
import ast

from .errors import Unsupported


class EnumMixin:
    @staticmethod
    def is_enum_class(node):
        return any((isinstance(b, ast.Name) and b.id == "Enum") or (isinstance(b, ast.Attribute) and b.attr == "Enum") for b in node.bases)

    def expand_enum(self, node):
        cname = node.name
        members, body, auto_n = [], [], 0
        has_str = has_repr = False
        for st in node.body:
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                v = st.value
                if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "auto" and not v.args:
                    auto_n += 1
                    v = ast.Constant(value=auto_n)
                elif isinstance(v, ast.Constant) and type(v.value) is int:
                    auto_n = max(auto_n, v.value)
                elif not (isinstance(v, ast.Constant) and isinstance(v.value, str)):
                    raise Unsupported(f"Enum {cname} : valeur du membre {st.targets[0].id} non supportée (int, str ou auto())", st)
                members.append((st.targets[0].id, v))
            elif isinstance(st, ast.FunctionDef):
                has_str |= st.name == "__str__"
                has_repr |= st.name == "__repr__"
                body.append(st)
            elif isinstance(st, ast.Pass) or (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant)):
                continue
            else:
                raise Unsupported(f"Enum {cname} : instruction non supportée dans le corps", st)
        if not members:
            raise Unsupported(f"Enum {cname} sans membre", node)
        kinds = {type(v.value) for _, v in members}
        if kinds not in ({int}, {str}):
            raise Unsupported(f"Enum {cname} : toutes les valeurs doivent être des int, ou toutes des str", node)
        vt = "int" if kinds == {int} else "str"
        src = (f"class {cname}:\n    def __init__(self, name: str, value: {vt}) -> None:\n        self.name = name\n        self.value = value\n")
        if not has_str:
            src += f"    def __str__(self) -> str:\n        return \"{cname}.\" + self.name\n"
        if not has_repr:
            src += f"    def __repr__(self) -> str:\n        return \"<{cname}.\" + self.name + \": \" + repr(self.value) + \">\"\n"
        gen = ast.parse(src).body[0]
        cls = ast.ClassDef(name=cname, bases=[], keywords=[], body=gen.body + body, decorator_list=[])
        stmts = [ast.parse(f'{cname}_{n} = {cname}("{n}", {ast.unparse(v)})').body[0] for n, v in members]
        lookup = "".join(f"    if v == {ast.unparse(val)}:\n        return {cname}_{n}\n" for n, val in members)
        fd = ast.parse(f"def {cname}_from_value(v: {vt}) -> {cname}:\n{lookup}    raise ValueError(f\"{{v!r}} is not a valid {cname}\")\n").body[0]
        for n in [cls, fd] + stmts:
            ast.copy_location(n, node)
            ast.fix_missing_locations(n)
            for sub in ast.walk(n):
                if hasattr(sub, "lineno"):
                    sub.lineno = node.lineno
                    sub.end_lineno = node.lineno
        return cls, stmts, fd, [(n, f"{cname}_{n}") for n, _ in members], vt

    def class_var_stmts(self, info, st):
        """`n: int = 0` / `n = 0` dans le corps d'une classe ordinaire -> instruction de module `A_n = 0`."""
        if isinstance(st, ast.AnnAssign):
            attr = st.target.id
        else:
            attr = st.targets[0].id
        gname = f"{info.name}_{attr}"
        known = dict(info.classvars)
        value = st.value

        class Local(ast.NodeTransformer):
            def visit_Name(self, n):
                return ast.copy_location(ast.Name(id=known[n.id], ctx=n.ctx), n) if n.id in known else n

        value = Local().visit(value)
        if isinstance(st, ast.AnnAssign):
            new = ast.AnnAssign(target=ast.Name(id=gname, ctx=ast.Store()), annotation=st.annotation, value=value, simple=1)
        else:
            new = ast.Assign(targets=[ast.Name(id=gname, ctx=ast.Store())], value=value)
        ast.copy_location(new, st)
        ast.fix_missing_locations(new)
        info.classvars[attr] = gname
        return new

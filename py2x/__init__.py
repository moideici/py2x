"""py2x : convertisseur d'un sous-ensemble typé de Python vers C++ et Kotlin."""
import ast

from .emit_cpp import CppEmitter
from .emit_kotlin import KotlinEmitter
from .errors import Unsupported
from .frontend import Frontend

TARGETS = {"cpp": CppEmitter, "kotlin": KotlinEmitter}


def _has_empty_literal(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.List) and not n.elts:
            return True
        if isinstance(n, ast.Dict) and not n.keys:
            return True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("list", "dict") and not n.args:
            return True
        if isinstance(n, ast.Call) and (n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")) in (
                "deque", "set", "defaultdict", "Counter", "OrderedDict", "heappush"):
            return True
        if isinstance(n, (ast.Set, ast.SetComp)):
            return True
    return False


def to_ir(source, strict=False, warnings=None):
    """Source -> IR. Les littéraux vides ([] {} list() dict()) sont typés par inférence : des passes « à blanc » collectent
    des indices (append, retour, argument, affectation...) jusqu'à stabilité, puis la vraie passe les utilise."""
    hints = {}
    if _has_empty_literal(ast.parse(source)):
        for _ in range(6):
            fe = Frontend(hints, dry=True, strict=strict)
            try:
                fe.convert(source)
            except Unsupported:
                pass
            hints = fe.hints
            if not fe.changed:
                break
    fe = Frontend(hints, dry=False, strict=strict)
    module = fe.convert(source)
    if warnings is not None:
        warnings.extend(fe.warnings)
    return module


def transpile(source, target, strict=False, warnings=None, runtime=True, package=None, camel=False):
    """Source Python -> code C++ ("cpp") ou Kotlin ("kotlin"). Lève Unsupported hors du sous-ensemble.
    strict=False : un int passé là où un float est annoté est converti (avertissement dans `warnings`) ; strict=True : refusé."""
    module = to_ir(source, strict, warnings)
    if target == "kotlin":
        TARGETS[target].camel = camel
        return TARGETS[target]().emit(module, runtime=runtime, package=package)
    return TARGETS[target]().emit(module)

"""Hiérarchie des exceptions Python prises en charge (nom -> classe parente). `Exception` est la racine (BaseException n'est pas supportée)."""

BUILTIN_EXC = {
    "Exception": None,
    "ArithmeticError": "Exception",
    "ZeroDivisionError": "ArithmeticError",
    "OverflowError": "ArithmeticError",
    "LookupError": "Exception",
    "IndexError": "LookupError",
    "KeyError": "LookupError",
    "ValueError": "Exception",
    "TypeError": "Exception",
    "AttributeError": "Exception",
    "NameError": "Exception",
    "EOFError": "Exception",
    "StopIteration": "Exception",
    "AssertionError": "Exception",
    "RuntimeError": "Exception",
    "NotImplementedError": "RuntimeError",
    "RecursionError": "RuntimeError",
}


def ancestors(name, user_bases):
    """Chaîne name, parent, grand-parent... ; `user_bases` : nom de classe utilisateur -> parent."""
    out = []
    while name is not None:
        out.append(name)
        name = user_bases[name] if name in user_bases else BUILTIN_EXC.get(name)
    return out

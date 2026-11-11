"""Tests du convertisseur.

  python -m unittest discover -s tests                 # rapide : conversion + messages d'erreur, rien n'est compilé
  PY2X_COMPILE=cpp     python -m unittest ...          # + compile et exécute le C++, compare à Python
  PY2X_COMPILE=kotlin  python -m unittest ...          # + idem Kotlin (plus lent : kotlinc)
  PY2X_COMPILE=cpp,kotlin ...                          # les deux
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from py2x import Unsupported, transpile  # noqa: E402
from py2x.verify import check  # noqa: E402

EXAMPLES = sorted((ROOT / "examples").glob("*.py"))
COMPILE = set(filter(None, os.environ.get("PY2X_COMPILE", "").split(",")))


class TestConversion(unittest.TestCase):
    def test_examples_convert(self):
        for p in EXAMPLES:
            for target in ("cpp", "kotlin"):
                with self.subTest(example=p.name, target=target):
                    code = transpile(p.read_text(encoding="utf-8"), target)
                    self.assertIn("main", code)

    def test_floor_semantics_emitted(self):
        src = "def f(a: int, b: int) -> int:\n    return a // b + a % b\n"
        self.assertIn("py_floordiv", transpile(src, "cpp"))
        self.assertIn("Math.floorDiv", transpile(src, "kotlin"))



    def test_lists_are_shared_handles_in_cpp(self):
        # une liste passée à une fonction est une poignée partagée (alias Python) : plus de const&/& selon la mutation
        src = ("def g(xs: list[int]) -> None:\n    xs.append(1)\n\n"
               "def h(xs: list[int]) -> int:\n    return len(xs)\n")
        cpp = transpile(src, "cpp")
        self.assertIn("void g(PyList<long long> xs)", cpp)
        self.assertIn("long long h(PyList<long long> xs)", cpp)

    def test_reassigned_param_shadowed_in_kotlin(self):
        src = "def f(n: int) -> int:\n    n += 1\n    return n\n"
        self.assertIn("var n = n", transpile(src, "kotlin"))

    def test_reserved_names_mangled(self):
        src = "def f(val: int, class_: int) -> int:\n    new: int = val + class_\n    return new\n"
        self.assertIn("val_", transpile(src, "kotlin"))
        self.assertIn("new_", transpile(src, "cpp"))


class TestUnsupported(unittest.TestCase):
    def raises(self, src, fragment, strict=False):
        with self.assertRaises(Unsupported) as cm:
            transpile(src, "cpp", strict=strict)
        self.assertIn(fragment, str(cm.exception))
        return str(cm.exception)

    def test_set_of_floats_unsupported(self):
        msg = self.raises("def f() -> int:\n    return len({float(i) for i in range(3)})\n", "set de float")
        self.assertIn("ligne 2", msg)

    def test_string_set_iteration_unsupported(self):
        self.raises("def f(s: set[str]) -> int:\n    n = 0\n    for w in s:\n        n += 1\n    return n\n", "varie d'une exécution")

    def test_bare_generator_unsupported(self):
        self.raises("def f(xs: list[int]) -> int:\n    g = (x for x in xs)\n    return 1\n", "expression génératrice")



    def test_enumerate_is_an_iterator(self):
        self.raises("def f(xs: list[int]) -> None:\n    print(enumerate(xs))\n", "itérateur")

    def test_any_needs_bools(self):
        self.raises("def f(xs: list[int]) -> bool:\n    return any(xs)\n", "liste de bool")

    def test_comprehension_variable_is_local(self):
        # la variable de compréhension ne fuit pas : x reste utilisable (et déclarable) après
        transpile("def f() -> int:\n    ys = [x for x in range(3)]\n    x = 5\n    return x + len(ys)\n", "cpp")

    def test_missing_annotation(self):
        self.raises("def f(x) -> int:\n    return 1\n", "sans annotation")

    def test_missing_return_annotation(self):
        self.raises("def f(x: int):\n    return 1\n", "annotation de retour")

    # --- classes et dataclasses ---
    def test_inheritance(self):
        self.raises("class A:\n    pass\n\nclass C:\n    pass\n\nclass B(A, C):\n    pass\n", "héritage multiple")

    def test_unknown_base_class(self):
        self.raises("class B(Thread):\n    pass\n", "classe parente")

    def test_raise_requires_exception(self):
        self.raises("class A:\n    pass\n\ndef f() -> None:\n    raise A()\n", "exception")

    def test_bare_raise_outside_except(self):
        self.raises("def f() -> None:\n    raise\n", "en dehors d'un bloc except")

    def test_return_in_finally(self):
        self.raises("def f() -> int:\n    try:\n        return 1\n    finally:\n        return 2\n", "finally")

    def test_class_variable(self):
        self.raises("class A:\n    n: int = 0\n\ndef f(a: A) -> None:\n    a.n = 3\n", "variable de classe")

    def test_unsupported_decorator_on_class(self):
        self.raises("@staticmethod\nclass A:\n    pass\n", "décorateur")

    def test_unknown_method_decorator_unsupported(self):
        self.raises("class A:\n    @cached\n    def f(self) -> int:\n        return 1\n", "décorateur")

    def test_special_method_unsupported(self):
        self.raises("class A:\n    def __iter__(self) -> int:\n        return 1\n", "méthode spéciale")

    def test_unknown_field(self):
        self.raises("class A:\n    def __init__(self) -> None:\n        self.x: int = 1\n\ndef f(a: A) -> int:\n    return a.y\n", "champ inconnu")

    def test_frozen_dataclass_is_immutable(self):
        self.raises("from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass P:\n    x: int\n\n"
                    "def f(p: P) -> None:\n    p.x = 2\n", "figée")

    def test_print_object_without_str(self):
        self.raises("class A:\n    def __init__(self) -> None:\n        self.x: int = 1\n\ndef f(a: A) -> None:\n    print(a)\n",
                    "adresse mémoire")

    def test_str_only_not_usable_in_list(self):
        self.raises("class A:\n    def __init__(self) -> None:\n        self.x: int = 1\n    def __str__(self) -> str:\n"
                    "        return \"a\"\n\ndef f(a: A) -> None:\n    print([a])\n", "adresse mémoire")




    def test_missing_required_argument(self):
        self.raises("from dataclasses import dataclass\n\n@dataclass\nclass A:\n    x: int\n    y: int\n\n"
                    "def f() -> A:\n    return A(1)\n", "manquant")

    def test_dataclass_field_order(self):
        self.raises("from dataclasses import dataclass\n\n@dataclass\nclass A:\n    x: int = 0\n    y: int\n", "sans valeur par défaut")

    def test_float_default_must_be_float(self):
        self.raises("from dataclasses import dataclass\n\n@dataclass\nclass A:\n    x: float = 0\n", "écrivez 0.0")

    def test_self_as_value_in_init(self):
        self.raises("class A:\n    def __init__(self, xs: list[\"A\"]) -> None:\n        xs.append(self)\n", "__init__")



    def test_slice_on_dict_unsupported(self):
        self.raises("def f(d: dict[int, int]) -> int:\n    return len(d[1:2])\n", "découpage non supporté")

    def test_empty_list_needs_annotation(self):
        self.raises("def f() -> int:\n    x = []\n    return 0\n", "annotez")

    def test_loop_variable_not_assignable(self):
        self.raises("def f() -> None:\n    for i in range(3):\n        i = 2\n", "variable de boucle")

    def test_loop_variable_not_visible_after(self):
        self.raises("def f() -> int:\n    for i in range(3):\n        pass\n    return i\n", "variable")

    def test_mixed_types(self):
        self.raises("def f(a: int, b: str) -> int:\n    return a + b\n", "non supporté entre")

    def test_and_or_on_mixed_types_in_value(self):
        self.raises("def f(a: int, b: str) -> int:\n    return a or b\n", "non booléennes")

    def test_import(self):
        self.raises("import os\n", "ligne 1")

    # Python ne convertit pas un int en float à l'affectation / au passage d'argument / au retour :
    # print(x) afficherait 3 et non 3.0. On refuse plutôt que de diverger (trouvé par le fuzzer).
    def test_int_assigned_to_float_variable(self):
        self.raises("def f() -> None:\n    x: float = 3\n", "n'est pas converti en float", strict=True)

    def test_int_passed_to_float_parameter(self):
        self.raises("def g(x: float) -> float:\n    return x\n\ndef f() -> float:\n    return g(2)\n", "n'est pas converti en float", strict=True)

    def test_int_returned_as_float(self):
        self.raises("def f() -> float:\n    return 1\n", "n'est pas converti en float", strict=True)

    def test_int_to_float_is_converted_with_a_warning_by_default(self):
        warnings = []
        code = transpile("def f() -> float:\n    return 1\n", "cpp", warnings=warnings)
        self.assertIn("double", code)
        self.assertTrue(any("int utilisé là où float" in w for w in warnings))

    def test_int_arithmetic_is_overflow_checked(self):
        src = "def f(a: int, b: int) -> int:\n    return a * b + (a << 2)\n"
        self.assertIn("py_mul", transpile(src, "cpp"))
        self.assertIn("pyMul", transpile(src, "kotlin"))

    def test_min_max_mixed_int_float(self):
        self.raises("def f(a: int, b: float) -> float:\n    return min(a, b)\n", "mélange int et float")

    def test_ternary_mixed_branches(self):
        self.raises("def f(c: bool) -> float:\n    return 1 if c else 2.5\n", "types différents")

    def test_mixed_list_literal(self):
        self.raises("def f() -> None:\n    xs: list[float] = [1, 2.5]\n", "n'est pas converti en float", strict=True)

    # --- tuples et vues de dict ---
    def test_dict_view_cannot_be_printed(self):
        self.raises("def f(d: dict[str, int]) -> None:\n    print(d.keys())\n", "est une vue en Python")

    def test_dict_view_cannot_be_assigned(self):
        self.raises("def f(d: dict[str, int]) -> None:\n    ks = d.items()\n", "est une vue en Python")

    def test_tuples_are_immutable(self):
        self.raises("def f(t: tuple[int, int]) -> None:\n    t[0] = 1\n", "immuables")

    def test_tuple_index_must_be_constant(self):
        self.raises("def f(t: tuple[int, int], i: int) -> int:\n    return t[i]\n", "constante")



    def test_unpack_arity_mismatch(self):
        self.raises("def f(t: tuple[int, int]) -> None:\n    a, b, c = t\n", "dépaquetage")

    def test_for_unpack_needs_tuples(self):
        self.raises("def f(xs: list[int]) -> None:\n    for a, b in xs:\n        pass\n", "un tuple est attendu")

    def test_float_in_tuple_strict(self):
        self.raises("def f() -> None:\n    t: tuple[float, int] = (1, 2)\n", "incompatible")

    # --- list/dict = références partagées (alias exact comme en Python) : ces programmes sont acceptés ---
    def test_alias_is_accepted(self):
        transpile("def f(a: list[int]) -> int:\n    b = a\n    b.append(1)\n    return len(a)\n", "cpp")
        transpile("def f(a: list[int]) -> int:\n    b = a\n    b.append(1)\n    return len(a)\n", "kotlin")

    def test_tuple_with_list_accepted(self):
        transpile("def f() -> tuple[int, list[int]]:\n    return 1, [2, 3]\n", "cpp")

    def test_return_field_list_accepted(self):
        transpile("class A:\n    def __init__(self) -> None:\n        self.xs: list[int] = []\n"
                  "    def get(self) -> list[int]:\n        return self.xs\n", "cpp")

    def test_repeat_nested_list_accepted(self):
        transpile("def f() -> list[list[int]]:\n    return [[0]] * 3\n", "cpp")

    def test_items_with_list_values_accepted(self):
        transpile("def f(d: dict[str, list[int]]) -> int:\n    t = 0\n    for k, v in d.items():\n        t += len(v)\n    return t\n", "cpp")

    def test_arithmetic_still_promotes(self):
        # ici Python promeut aussi : 2 + 0.5 est un float
        transpile("def f(a: int, b: float) -> float:\n    return a + b * 2 - a / 3\n", "cpp")


@unittest.skipUnless(COMPILE, "définir PY2X_COMPILE=cpp,kotlin pour compiler et exécuter")
class TestRoundtrip(unittest.TestCase):
    pass


def _make(example, target):
    def t(self):
        ok, detail = check(example, target)
        self.assertTrue(ok, f"{example.name} -> {target}\n{detail}")
    return t


for _p in EXAMPLES:
    for _t in ("cpp", "kotlin"):
        if _t in COMPILE:
            setattr(TestRoundtrip, f"test_{_p.stem}_{_t}", _make(_p, _t))

if __name__ == "__main__":
    unittest.main()

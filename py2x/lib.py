"""Bibliothèque standard supportée : fonctions et constantes de math, string, sys.

Chaque fonction : types d'arguments, type de retour, et le modèle de code C++ / Kotlin ({0}, {1} = arguments déjà émis).
Types d'arguments : "num" (int ou float, promu en float), "int", "str".
"""
import math

from .types import BOOL, FLOAT, INT, NONE, STR


class Fn:
    def __init__(self, args, ret, cpp, kt):
        self.args, self.ret, self.cpp, self.kt = args, ret, cpp, kt


def fn(args, ret, cpp, kt):
    return Fn(args if isinstance(args, list) else [args], ret, cpp, kt)


M1 = ["num"]
M2 = ["num", "num"]


def _m(name, cpp=None, kt=None, args=M1, ret=FLOAT):
    return fn(args, ret, cpp or f"std::{name}({{0}})", kt or f"Math.{name}({{0}})")


LIB = {
    "math.sqrt": _m("sqrt", cpp="py_sqrt({0})", kt="pySqrt({0})"), "math.exp": _m("exp", cpp="py_exp({0})", kt="pyExp({0})"),
    "math.log10": _m("log10", cpp="py_log10({0})", kt="pyLog10({0})"), "math.log2": _m("log2", cpp="py_log2({0})", kt="pyLog2({0})"),
    "math.log1p": _m("log1p", cpp="py_log1p({0})", kt="pyLog1p({0})"), "math.expm1": _m("expm1", cpp="py_expm1({0})", kt="pyExpm1({0})"),
    "math.copysign": _m("copysign", args=M2, cpp="std::copysign({0}, {1})", kt="Math.copySign({0}, {1})"),
    "math.isclose": _m("isclose", args=M2, ret=BOOL, cpp="py_isclose({0}, {1})", kt="pyIsclose({0}, {1})"),
    "math.comb": fn(["int", "int"], INT, "py_comb({0}, {1})", "pyComb({0}, {1})"),
    "math.perm": fn(["int", "int"], INT, "py_perm({0}, {1})", "pyPerm({0}, {1})"),
    "math.sin": _m("sin"), "math.cos": _m("cos"), "math.tan": _m("tan"), "math.asin": _m("asin", cpp="py_asin({0})", kt="pyAsin({0})"), "math.acos": _m("acos", cpp="py_acos({0})", kt="pyAcos({0})"),
    "math.atan": _m("atan"), "math.sinh": _m("sinh"), "math.cosh": _m("cosh"), "math.tanh": _m("tanh"),
    "math.fabs": _m("fabs", kt="Math.abs({0})"),
    "math.atan2": _m("atan2", args=M2, cpp="std::atan2({0}, {1})", kt="Math.atan2({0}, {1})"),
    "math.hypot": _m("hypot", args=M2, cpp="std::hypot({0}, {1})", kt="Math.hypot({0}, {1})"),
    "math.pow": _m("pow", args=M2, cpp="py_mpow({0}, {1})", kt="pyMpow({0}, {1})"),
    "math.degrees": _m("degrees", cpp="({0} * (180.0 / 3.141592653589793))", kt="Math.toDegrees({0})"),
    "math.radians": _m("radians", cpp="({0} * (3.141592653589793 / 180.0))", kt="Math.toRadians({0})"),
    "math.floor": _m("floor", ret=INT, cpp="py_f2i(std::floor({0}))", kt="pyF2i(Math.floor({0}))"),
    "math.ceil": _m("ceil", ret=INT, cpp="py_f2i(std::ceil({0}))", kt="pyF2i(Math.ceil({0}))"),
    "math.trunc": _m("trunc", ret=INT, cpp="py_f2i(std::trunc({0}))", kt="pyF2i({0})"),
    "math.isnan": _m("isnan", ret=BOOL, cpp="std::isnan({0})", kt="({0}).isNaN()"),
    "math.isinf": _m("isinf", ret=BOOL, cpp="std::isinf({0})", kt="({0}).isInfinite()"),
    "math.isfinite": _m("isfinite", ret=BOOL, cpp="std::isfinite({0})", kt="({0}).isFinite()"),
    "math.gcd": fn(["int", "int"], INT, "py_gcd({0}, {1})", "pyGcd({0}, {1})"),
    "math.lcm": fn(["int", "int"], INT, "py_lcm({0}, {1})", "pyLcm({0}, {1})"),
    "math.isqrt": fn(["int"], INT, "py_isqrt({0})", "pyIsqrt({0})"),
    "math.factorial": fn(["int"], INT, "py_factorial({0})", "pyFactorial({0})"),
    "sys.exit": fn(["int"], NONE, "std::exit((int)({0}))", "kotlin.system.exitProcess(({0}).toInt())"),
}

# math.log accepte 1 ou 2 arguments
LOG = {1: ("py_log({0})", "pyLog({0})"), 2: ("py_fdiv(py_log({0}), py_log({1}))", "pyFdiv(pyLog({0}), pyLog({1}))")}

# constantes : (type, valeur Python, modèle C++, modèle Kotlin)
CONSTS = {
    "math.pi": (FLOAT, math.pi, repr(math.pi), repr(math.pi)),
    "math.e": (FLOAT, math.e, repr(math.e), repr(math.e)),
    "math.tau": (FLOAT, math.tau, repr(math.tau), repr(math.tau)),
    "math.inf": (FLOAT, math.inf, "std::numeric_limits<double>::infinity()", "Double.POSITIVE_INFINITY"),
    "math.nan": (FLOAT, math.nan, "std::numeric_limits<double>::quiet_NaN()", "Double.NaN"),
    "sys.maxsize": (INT, 2 ** 63 - 1, "9223372036854775807LL", "Long.MAX_VALUE"),
}

# constantes de chaînes du module string : inlinées
STRING_CONSTS = {
    "string.ascii_lowercase": "abcdefghijklmnopqrstuvwxyz",
    "string.ascii_uppercase": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "string.ascii_letters": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "string.digits": "0123456789",
    "string.hexdigits": "0123456789abcdefABCDEF",
    "string.octdigits": "01234567",
    "string.punctuation": "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
    "string.whitespace": " \t\n\r\x0b\x0c",
}

MODULES = {"math", "string", "sys"}
IGNORED_MODULES = {"typing", "__future__", "dataclasses", "abc", "collections.abc", "enum"}

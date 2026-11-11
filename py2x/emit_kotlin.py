"""Émetteur Kotlin (JVM). int -> Long, float -> Double, str -> String, list -> MutableList, dict -> MutableMap (ordre d'insertion)."""
import re

from . import ir
from .lib import CONSTS, LIB, LOG
from .names import KOTLIN_RESERVED, func_name, mangle
from .runtime_kt_coll import COLLECTIONS
from .runtime_kt_exc import EXC_KT
from .runtime_kt_str import FORMAT, STRINGS
from .types import BOOL, FLOAT, INT, NONE, STR

PRELUDE = r'''// --- runtime py2x : reproduit la sémantique de Python ---
fun <T> List<T>.pyIdx(i: Long): Int {
    val n = this.size
    val j = if (i < 0) i + n else i
    if (j < 0 || j >= n) throw IndexError("list index out of range")
    return j.toInt()
}
fun CharSequence.pyIdx(i: Long): Int {
    val n = this.length
    val j = if (i < 0) i + n else i
    if (j < 0 || j >= n) throw IndexError("string index out of range")
    return j.toInt()
}
fun pyAdd(a: Long, b: Long): Long { val r = a + b; if (((a xor r) and (b xor r)) < 0) throw OverflowError("int too large: the translation uses 64-bit integers"); return r }
fun pySub(a: Long, b: Long): Long { val r = a - b; if (((a xor b) and (a xor r)) < 0) throw OverflowError("int too large: the translation uses 64-bit integers"); return r }
fun pyMul(a: Long, b: Long): Long {
    val hi = Math.multiplyHigh(a, b)
    val lo = a * b
    if ((hi == 0L && lo >= 0) || (hi == -1L && lo < 0)) return lo
    throw OverflowError("int too large: the translation uses 64-bit integers")
}
fun pyNeg(a: Long): Long { if (a == Long.MIN_VALUE) throw OverflowError("int too large: the translation uses 64-bit integers"); return -a }
fun pyAbs(a: Long): Long = if (a < 0) pyNeg(a) else a
fun pyShl(a: Long, b: Long): Long {
    if (b < 0) throw ValueError("negative shift count")
    if (a == 0L) return 0L
    if (b >= 63) throw OverflowError("int too large: the translation uses 64-bit integers")
    val r = a shl b.toInt()
    if ((r shr b.toInt()) != a) throw OverflowError("int too large: the translation uses 64-bit integers")
    return r
}
fun pyShr(a: Long, b: Long): Long {
    if (b < 0) throw ValueError("negative shift count")
    return if (b >= 63) (if (a < 0) -1L else 0L) else (a shr b.toInt())
}
fun pySumI(x: List<Long>): Long { var s = 0L; for (v in x) s = pyAdd(s, v); return s }
fun ipow(a: Long, b: Long): Long {
    if (b < 0) throw ValueError("negative exponent")
    var r = 1L
    var x = a
    var e = b
    while (e > 0) {
        if ((e and 1L) == 1L) r = pyMul(r, x)
        e = e shr 1
        if (e > 0) x = pyMul(x, x)
    }
    return r
}
fun pyFloorDiv(a: Long, b: Long): Long { if (b == 0L) throw ZeroDivisionError("integer division or modulo by zero"); return Math.floorDiv(a, b) }
fun pyFloorMod(a: Long, b: Long): Long { if (b == 0L) throw ZeroDivisionError("integer division or modulo by zero"); return Math.floorMod(a, b) }
fun pyDiv(a: Double, b: Double): Double { if (b == 0.0) throw ZeroDivisionError("division by zero"); return a / b }
fun pyFdiv(a: Double, b: Double): Double { if (b == 0.0) throw ZeroDivisionError("float division by zero"); return a / b }
fun <T : Comparable<T>> pyMinList(x: List<T>): T { if (x.isEmpty()) throw ValueError("min() arg is an empty sequence"); return x.min() }
fun <T : Comparable<T>> pyMaxList(x: List<T>): T { if (x.isEmpty()) throw ValueError("max() arg is an empty sequence"); return x.max() }
fun pyFloat(x: Double): String {
    if (x.isNaN()) return "nan"
    if (x.isInfinite()) return if (x > 0) "inf" else "-inf"
    if (x == 0.0) return if (1.0 / x < 0) "-0.0" else "0.0"
    var bd = java.math.BigDecimal(x)
    for (p in 1..17) {
        val c = java.math.BigDecimal(x).round(java.math.MathContext(p))
        if (c.toDouble() == x) { bd = c; break }
    }
    bd = bd.stripTrailingZeros()
    val a = Math.abs(x)
    if (a >= 1e-4 && a < 1e16) {
        val p = bd.toPlainString()
        return if (p.contains('.')) p else p + ".0"
    }
    val digits = bd.unscaledValue().abs().toString()
    val exp = digits.length - 1 - bd.scale()
    val mant = if (digits.length == 1) digits else digits.substring(0, 1) + "." + digits.substring(1)
    return (if (x < 0) "-" else "") + mant + "e" + (if (exp < 0) "-" else "+") + String.format("%02d", Math.abs(exp))
}
interface PyTuple { fun items(): List<Any?> }
@Suppress("UNCHECKED_CAST")
fun pyCmpAny(x: Any?, y: Any?): Int {
    if (x is List<*> && y is List<*>) {
        val n = minOf(x.size, y.size)
        for (i in 0 until n) { val c = pyCmpAny(x[i], y[i]); if (c != 0) return c }
        return x.size.compareTo(y.size)
    }
    return (x as Comparable<Any?>).compareTo(y)
}
fun pyCmpAll(a: List<Any?>, b: List<Any?>): Int {
    for (i in a.indices) {
        val c = pyCmpAny(a[i], b[i])
        if (c != 0) return c
    }
    return 0
}
fun <T> pyRepeat(xs: List<T>, n: Long): MutableList<T> {
    val r = mutableListOf<T>()
    var i = 0L
    while (i < n) { r.addAll(xs); i++ }
    return r
}
fun pyRepeatStr(s: String, n: Long): String {
    val sb = StringBuilder()
    var i = 0L
    while (i < n) { sb.append(s); i++ }
    return sb.toString()
}
fun <T> MutableList<T>.pyPop(i: Long): T {
    val n = this.size
    if (n == 0) throw IndexError("pop from empty list")
    val j = if (i < 0) i + n else i
    if (j < 0 || j >= n) throw IndexError("pop index out of range")
    return this.removeAt(j.toInt())
}
fun <T> MutableList<T>.pyInsert(i: Long, x: T) {
    val n = this.size
    var j = if (i < 0) i + n else i
    if (j < 0) j = 0
    if (j > n) j = n.toLong()
    this.add(j.toInt(), x)
}
fun <T> List<T>.pyCount(x: T): Long = this.count { it == x }.toLong()
fun <T> List<T>.pyIndex(x: T): Long {
    val i = this.indexOf(x)
    if (i < 0) throw ValueError(pyRepr(x) + " is not in list")
    return i.toLong()
}
fun <T> MutableList<T>.pyRemove(x: T) {
    val i = this.indexOf(x)
    if (i < 0) throw ValueError("list.remove(x): x not in list")
    this.removeAt(i)
}
fun pyGcd(a: Long, b: Long): Long {
    var x = Math.abs(a)
    var y = Math.abs(b)
    while (y != 0L) { val t = x % y; x = y; y = t }
    return x
}
fun pyLcm(a: Long, b: Long): Long = if (a == 0L || b == 0L) 0L else pyAbs(pyMul(a / pyGcd(a, b), b))
fun pyIsqrt(n: Long): Long {
    if (n < 0) throw ValueError("isqrt() argument must be nonnegative")
    var r = Math.sqrt(n.toDouble()).toLong()
    while (r * r > n) r--
    while ((r + 1) * (r + 1) <= n) r++
    return r
}
fun pyFactorial(n: Long): Long {
    if (n < 0) throw ValueError("factorial() not defined for negative values")
    var r = 1L
    var i = 2L
    while (i <= n) { r = pyMul(r, i); i++ }
    return r
}
fun <T : Any> pyNn(x: T?): T = x ?: throw TypeError("opération non supportée sur None")
fun <T : Any> pyNnAttr(x: T?): T = x ?: throw AttributeError("'NoneType' object has no attribute")
interface PyObj { fun pyStrObj(): String; fun pyReprObj(): String }
fun pyReprStr(s: String): String {
    val q = if (s.contains('\'') && !s.contains('"')) '"' else '\''
    val sb = StringBuilder()
    sb.append(q)
    for (c in s) {
        when {
            c == '\\' -> sb.append("\\\\")
            c == q -> { sb.append('\\'); sb.append(c) }
            c == '\n' -> sb.append("\\n")
            c == '\t' -> sb.append("\\t")
            c == '\r' -> sb.append("\\r")
            c.code < 32 || c.code == 127 -> sb.append(String.format("\\x%02x", c.code))
            else -> sb.append(c)
        }
    }
    sb.append(q)
    return sb.toString()
}
fun pyRepr(x: Any?): String = if (x == null) "None" else if (x is String) pyReprStr(x) else if (x is PyObj) x.pyReprObj() else pyStr(x)
fun pyStr(x: Any?): String = when (x) {
    null -> "None"
    is Boolean -> if (x) "True" else "False"
    is Double -> pyFloat(x)
    is String -> x
    is PyObj -> x.pyStrObj()
    is PyTuple -> { val xs = x.items(); if (xs.size == 1) "(" + pyRepr(xs[0]) + ",)" else xs.joinToString(", ", "(", ")") { pyRepr(it) } }
    is PyDeque<*> -> x.str()
    is PyVTuple<*> -> x.str()
    is PySet<*> -> x.str()
    is List<*> -> x.joinToString(", ", "[", "]") { pyRepr(it) }
    is PyFlavDict<*, *> -> pyFlavStr(x)
    is Map<*, *> -> x.entries.joinToString(", ", "{", "}") { pyRepr(it.key) + ": " + pyRepr(it.value) }
    else -> x.toString()
}
// --- fin du runtime ---
'''

PRELUDE = PRELUDE.replace("// --- fin du runtime ---", EXC_KT + STRINGS + FORMAT + COLLECTIONS + "// --- fin du runtime ---")

CMP = {"==": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
BIT = {"&": "and", "|": "or", "^": "xor", "<<": "shl", ">>": "shr"}


def tup_class(n):
    """Tuple Python de n éléments : data class (égalité/hash structurels, utilisable comme clé de dict) comparable."""
    tp = ", ".join(chr(65 + i) for i in range(n))
    fields = ", ".join(f"val f{i}: {chr(65 + i)}" for i in range(n))
    items = ", ".join(f"f{i}" for i in range(n))
    return (f"fun <A> Tup{n}<{', '.join(['A'] * n)}>.toL(): MutableList<A> = mutableListOf({items})\n"
            f"data class Tup{n}<{tp}>({fields}) : PyTuple, Comparable<Tup{n}<{tp}>> {{\n"
            f"    override fun items(): List<Any?> = listOf({items})\n"
            f"    override fun compareTo(other: Tup{n}<{tp}>): Int = pyCmpAll(items(), other.items())\n}}\n")


def kstr(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "$":
            out.append("\\$")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif o < 32 or o == 127:
            out.append("\\u%04x" % o)
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


class KotlinEmitter:
    def __init__(self):
        self.lines, self.ind = [], 0
        self.classes_by_name = {}
        self.cur_owner = None
        self.exc_vars = []
        self.n = 0

    @staticmethod
    def runtime_source(package=None):
        """Runtime seul (à générer UNE fois par projet quand plusieurs fichiers sont convertis avec runtime=False)."""
        head = f"package {package}\n\n" if package else ""
        return head + PRELUDE + "".join(tup_class(n) for n in range(1, 9)) + "\n"

    def emit(self, module, runtime=True, package=None):
        text, tups = self.emit_all(module)
        head = f"package {package}\n\n" if package else ""
        if not runtime:
            return head + text + "\n"
        return head + PRELUDE + "".join(tup_class(n) for n in tups) + "\n" + text + "\n"

    def emit_all(self, module):
        self.lib_mode = not module.has_main
        self.classes_by_name = {c.name: c for c in module.classes}
        body = ([self.class_def(c) for c in module.classes] + [self.decl(n, t) + "\n" for n, t in module.globals]
                + [self.func(f) for f in module.funcs])
        if module.entry is not None:
            body.append(self.func(module.entry, entry=True))
        text = "\n".join(body)
        arities = sorted({int(n) for n in re.findall(r"\bTup(\d)\b", text)})  # une classe par taille de tuple réellement utilisée
        return text, arities

    def ty(self, t):
        if t == INT:
            return "Long"
        if t == FLOAT:
            return "Double"
        if t == BOOL:
            return "Boolean"
        if t == STR:
            return "String"
        if t == NONE:
            return "Unit"
        if t.kind == "list":
            return f"MutableList<{self.ty(t.args[0])}>"
        if t.kind == "gen":
            return f"Iterator<{self.ty(t.args[0])}>"
        if t.kind == "func":
            return f"({', '.join(self.ty(a) for a in t.args[1:])}) -> {self.ty(t.args[0])}"
        if t.kind == "vtuple":
            return f"PyVTuple<{self.ty(t.args[0])}>"
        if t.kind == "set":
            return f"PySet<{self.ty(t.args[0])}>"
        if t.kind == "deque":
            return f"PyDeque<{self.ty(t.args[0])}>"
        if t.kind == "tuple":
            return f"Tup{len(t.args)}<{', '.join(self.ty(a) for a in t.args)}>"
        if t.kind == "class":
            return self.cname(t.args[0])
        if t.kind == "optional":
            return self.ty(t.args[0]) + "?"
        return f"MutableMap<{self.ty(t.args[0])}, {self.ty(t.args[1])}>"

    def default(self, t):
        """Valeur par défaut d'un type, ou None s'il n'y en a pas (objets) : on utilise alors `lateinit var`."""
        if t == INT:
            return "0L"
        if t == FLOAT:
            return "0.0"
        if t == BOOL:
            return "false"
        if t == STR:
            return '""'
        if t.kind == "list":
            return f"mutableListOf<{self.ty(t.args[0])}>()"
        if t.kind == "optional":
            return "null"
        if t.kind == "func":
            return None
        if t.kind == "vtuple":
            return f"PyVTuple<{self.ty(t.args[0])}>(mutableListOf())"
        if t.kind == "set":
            return f"PySet<{self.ty(t.args[0])}>({'true' if t.args[0] in (INT, BOOL) else 'false'})"
        if t.kind == "deque":
            return f"PyDeque<{self.ty(t.args[0])}>(-1L)"
        if t.kind == "class":
            return None
        if t.kind == "tuple":
            ds = [self.default(a) for a in t.args]
            return None if any(d is None for d in ds) else f"{self.ty(t)}({', '.join(ds)})"
        return f"mutableMapOf<{self.ty(t.args[0])}, {self.ty(t.args[1])}>()"

    def decl(self, name, t, init=None):
        """Déclaration `var x: T = init` ; sans init : valeur par défaut, ou `lateinit var` si le type n'en a pas."""
        if init is None:
            init = self.default(t)
        if init is None:
            return f"lateinit var {self.var(name)}: {self.ty(t)}"
        return f"var {self.var(name)}: {self.ty(t)} = {init}"

    camel = False  # option --camel : snake_case -> camelCase pour les identifiants du programme (pas pour les noms py* du runtime)

    @classmethod
    def case(cls, name):
        if not cls.camel or name.startswith("py") or name.startswith("__"):
            return name
        lead = len(name) - len(name.lstrip("_"))
        return name[:lead] + re.sub(r"_+([A-Za-z0-9])", lambda m: m.group(1).upper(), name[lead:])

    def var(self, name):
        return mangle(self.case(name), KOTLIN_RESERVED)

    def cname(self, name):
        return "PyException" if name == "Exception" else mangle(name, KOTLIN_RESERVED)

    def mname(self, name):
        if name.startswith("__") and name.endswith("__") and name not in ("__str__", "__repr__", "__init__"):
            return "pyOp" + "".join(p.capitalize() for p in name[2:-2].split("_"))  # __len__ -> pyOpLen
        return {"__str__": "pyStrM", "__repr__": "pyReprM"}.get(name) or mangle(self.case(name), KOTLIN_RESERVED)

    # ---------- classes ----------
    def class_def_hier(self, c):
        """Classe d'une hiérarchie : `open class`, __init__ devient pyInit<Classe> appelé après la construction (Python exécute
        super().__init__() comme une instruction ordinaire, pas comme un appel au constructeur parent en tête de classe)."""
        n = self.cname(c.name)
        self.cur_owner = c
        cmp_ = f", Comparable<{n}>" if c.lt_root else ""
        if c.base is None:
            head = f"open class {n} : PyObj{cmp_} {{"
        elif c.is_exc and c.init_owner is None:
            head = f"open class {n}(vararg a: Any?) : {self.cname(c.base)}(*a) {{"
        else:
            head = f"open class {n} : {self.cname(c.base)}(){cmp_} {{"
        L = [head]
        for fn, ft, _ in c.fields:
            L.append("    " + self.decl(fn, ft))
        if c.is_exc or c.base is not None:
            L.append(f'    override fun pyName(): String = "{c.name}"')
        else:
            L.append(f'    open fun pyName(): String = "{c.name}"')
        if c.init is not None:
            L.append(self.func(c.init, in_class=True).rstrip("\n"))
        for m in c.methods:
            L.append(self.func(m, in_class=True).rstrip("\n"))
        if any(m.name == "__eq__" for m in c.methods):
            L.append(f"    override fun equals(other: Any?): Boolean = other is {n} && pyOpEq(other)")
            L.append("    override fun hashCode(): Int = 0")
        own_str = any(m.name == "__str__" for m in c.methods)
        own_repr = any(m.name == "__repr__" for m in c.methods)
        if c.base is None:  # racine non-exception : implémente PyObj
            L.append(f"    override fun pyReprObj(): String = {'pyReprM()' if c.has_repr else chr(34) + '<object>' + chr(34)}")
            L.append(f"    override fun pyStrObj(): String = {'pyStrM()' if c.has_str else 'pyReprObj()'}")
        else:
            if own_repr:
                L.append("    override fun pyReprObj(): String = pyReprM()")
            if own_str:
                L.append("    override fun pyStrObj(): String = pyStrM()")
        if c.lt_root:
            L.append(f"    override fun compareTo(other: {n}): Int = if (pyOpLt(other)) -1 else if (other.pyOpLt(this)) 1 else 0")
        L.append("}\n")
        self.cur_owner = None
        return "\n".join(L)

    def class_def(self, c):
        n = self.cname(c.name)
        if c.hier and not c.is_dataclass:
            return self.class_def_hier(c)
        self.cur_owner = c
        L = []
        if c.is_dataclass and c.fields:
            kw = "val" if c.frozen else "var"
            ps = ", ".join(f"{kw} {self.var(fn)}: {self.ty(ft)}" for fn, ft, _ in c.fields)
            cmp_ = f", Comparable<{n}>" if c.lt_root else ""
            L.append(f"data class {n}({ps}) : PyObj{cmp_} {{")  # equals/hashCode structurels, comme @dataclass(eq=True)
            if c.has_post_init:
                L.append("    init { pyOpPostInit() }")
            if c.nocompare:  # field(compare=False) : equals/hashCode ne portent que sur les autres champs
                cmp_fields = [self.var(fn) for fn, _, _ in c.fields if fn not in c.nocompare] or ["0"]
                L.append(f"    override fun equals(other: Any?): Boolean = other is {n} && " + " && ".join(
                    f"{f} == other.{f}" if f != "0" else "true" for f in cmp_fields))
                L.append("    override fun hashCode(): Int = listOf<Any?>(" + ", ".join(cmp_fields) + ").hashCode()")
        elif c.is_dataclass:
            L += [f"class {n} : PyObj {{", f"    override fun equals(other: Any?): Boolean = other is {n}", "    override fun hashCode(): Int = 0"]
        else:
            ps = ", ".join(f"{self.var(p)}: {self.ty(t)}" for p, t in c.init.params) if c.init is not None else ""
            L.append(f"class {n}({ps}) : PyObj{', Comparable<' + n + '>' if c.lt_root else ''} {{")  # égalité par défaut = identité, comme en Python
            for fn, ft, _ in c.fields:
                L.append("    " + self.decl(fn, ft))
        if c.init is not None:
            L.append(self.func(c.init, in_class=True).rstrip("\n"))
        for m in c.methods:
            L.append(self.func(m, in_class=True).rstrip("\n"))
        if any(m.name == "__eq__" for m in c.methods):
            L.append(f"    override fun equals(other: Any?): Boolean = other is {n} && pyOpEq(other)")
            L.append("    override fun hashCode(): Int = 0")
        if c.has_repr:
            repr_ = "pyReprM()"
        elif c.is_dataclass:
            parts = [f'"{c.name}("'] + [f'"{"" if i == 0 else ", "}{fn}=" + pyRepr({self.var(fn)})' for i, (fn, _, _) in enumerate(c.fields)]
            repr_ = " + ".join(parts) + ' + ")"' if c.fields else f'"{c.name}()"'
        else:
            repr_ = '"<object>"'
        L.append(f"    override fun pyReprObj(): String = {repr_}")
        L.append(f"    override fun pyStrObj(): String = {'pyStrM()' if c.has_str else 'pyReprObj()'}")
        if c.lt_root:
            L.append(f"    override fun compareTo(other: {n}): Int = if (pyOpLt(other)) -1 else if (other.pyOpLt(this)) 1 else 0")
        L.append("}\n")
        return "\n".join(L)

    def func(self, f, entry=False, in_class=False):
        base = 2 if in_class else 1
        self.in_gen = f.is_gen
        self.lines, self.ind = [], base
        for name in (p for p, _ in f.params if p in f.reassigned):
            self.w(f"var {self.var(name)} = {self.var(name)}")  # les paramètres Kotlin sont immuables
        for name, t in f.hoisted:
            self.w(self.decl(name, t))
        self.stmts(f.body)
        pad = "    " * (base - 1)
        hier = in_class and self.cur_owner is not None and self.cur_owner.hier
        if in_class and f.name == "__init__":
            if hier:
                ps = ", ".join(f"{self.var(n)}: {self.ty(t)}" for n, t in f.params)
                return f"{pad}fun pyInit{self.cname(f.owner)}({ps}) {{\n" + "\n".join(self.lines) + f"\n{pad}}}\n"
            return f"{pad}init {{\n" + "\n".join(self.lines) + f"\n{pad}}}\n"
        if f.is_gen and not entry:
            self.lines = ["    " * base + "return iterator {"] + ["    " + ln for ln in self.lines] + ["    " * base + "}"]
        if entry and getattr(self, "lib_mode", False):
            head = "private val pyModuleInit: Unit = run"  # bibliothèque : initialisation des constantes de module au chargement du fichier
        elif entry:
            self.lines.insert(0, "    " * base + 'System.setOut(java.io.PrintStream(java.io.FileOutputStream(java.io.FileDescriptor.out), true, "UTF-8"))  // sortie UTF-8 comme Python')
            head = "fun main()"
        else:
            ps = ", ".join(f"{self.var(n)}: {self.ty(t)}" for n, t in f.params)
            name = self.mname(f.name) if in_class else func_name(self.case(f.name), KOTLIN_RESERVED)
            mod = ("override " if f.name in self.cur_owner.overrides else "open ") if hier else ""
            head = f"{pad}{mod}fun {name}({ps})" + ("" if f.ret == NONE else f": {self.ty(f.ret)}")
            if in_class and self.camel and not mod and len(name) > 3 and name[:3] in ("get", "set") and self.cur_owner is not None:
                prop = name[3].lower() + name[4:]
                if any(self.var(fn) == prop for fn, _, _ in self.cur_owner.fields):  # setTheme() vs propriété `theme` : même signature JVM
                    head = f'{pad}@JvmName("{f.name}")' + chr(10) + head
        return head + " {\n" + "\n".join(self.lines) + f"\n{pad}}}\n"

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
        self.w(self.decl(s.name, s.type, None if s.init is None else self.x(s.init)))

    def s_Assign(self, s):
        self.w(f"{self.lvalue(s.target)} = {self.x(s.value)}")

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
        if not isinstance(s.step, int):
            self.w(f"for ({self.var(s.var)} in pyRange({self.x(s.start)}, {self.x(s.stop)}, {self.x(s.step)})) {{")
            self.block(s.body)
            self.w("}")
            return
        v, k = self.var(s.var), abs(s.step)
        step = f" step {k}L" if k != 1 else ""
        if s.step > 0:
            self.w(f"for ({v} in {self.x(s.start)} until {self.x(s.stop)}{step}) {{")
        else:
            self.w(f"for ({v} in {self.x(s.start)} downTo ({self.x(s.stop)} + 1L){step}) {{")
        self.block(s.body)
        self.w("}")

    def s_ForEach(self, s):
        it = self.x(s.iterable) + (".keys" if s.iterable.type.kind == "dict" else "")
        self.w(f"for ({self.var(s.var)} in {it}) {{")
        self.block(s.body)
        self.w("}")

    def bounds(self, lo, hi, step):
        return f"{'null' if lo is None else self.x(lo)}, {'null' if hi is None else self.x(hi)}, {self.x(step) if step is not None else '1L'}"

    def s_SliceAssign(self, s):
        self.w(f"pySetSlice({self.x(s.base)}, {self.bounds(s.lo, s.hi, s.step)}, {self.x(s.value)})")

    def s_Delete(self, s):
        b = self.x(s.base)
        if s.kind == "key":
            self.w(f"pyDelKey({b}, {self.x(s.args[0])})")
        elif s.kind == "item":
            self.w(f"pyDelItem({b}, {self.x(s.args[0])})")
        else:
            self.w(f"pyDelSlice({b}, {self.bounds(*s.args)})")

    def s_LocalFunc(self, s):
        f = s.func
        ps = ", ".join(f"{self.var(n)}: {self.ty(t)}" for n, t in f.params)
        self.w(f"fun {self.var(f.name)}({ps})" + ("" if f.ret == NONE else f": {self.ty(f.ret)}") + " {")
        self.ind += 1
        for name in (p for p, _ in f.params if p in f.reassigned):
            self.w(f"var {self.var(name)} = {self.var(name)}")
        for name, t in f.hoisted:
            self.w(self.decl(name, t))
        self.stmts(f.body)
        self.ind -= 1
        self.w("}")

    def s_Raise(self, s):
        self.w(f"throw {self.exc_vars[-1] if s.value is None else self.x(s.value)}")

    def s_Try(self, s):
        k = self.n
        self.n += 1
        if s.final:
            self.w("try {")
            self.ind += 1
        if s.orelse:
            self.w(f"var pyOk{k} = false")
        if s.handlers:
            self.w("try {")
            self.block(s.body)
            if s.orelse:
                self.w(f"    pyOk{k} = true")
            self.w(f"}} catch (pyEx{k}: PyException) {{")
            self.ind += 1
            self.exc_vars.append(f"pyEx{k}")
            first = True
            for h in s.handlers:
                if h.classes is None:
                    self.w("{" if first else "else {")
                else:
                    cond = " || ".join(f"pyEx{k} is {self.cname(c)}" for c in h.classes)
                    self.w(("if (" if first else "else if (") + cond + ") {")
                first = False
                if h.var:
                    self.ind += 1
                    self.w(f"val {self.var(h.var)}: {self.ty(h.vtype)} = pyEx{k}" + ("" if len(h.classes or []) <= 1 else f" as {self.ty(h.vtype)}"))
                    self.ind -= 1
                self.block(h.body)
                self.w("}")
            if all(h.classes is not None for h in s.handlers):
                self.w(f"else {{ throw pyEx{k} }}")
            self.exc_vars.pop()
            self.ind -= 1
            self.w("}")
        else:
            for st in s.body:
                getattr(self, "s_" + type(st).__name__)(st)
        if s.orelse:
            self.w(f"if (pyOk{k}) {{")
            self.block(s.orelse)
            self.w("}")
        if s.final:
            self.ind -= 1
            self.w("} finally {")
            self.block(s.final)
            self.w("}")

    def s_Return(self, s):
        if getattr(self, "in_gen", False):
            self.w("return@iterator")
            return
        self.w("return" if s.value is None else f"return {self.x(s.value)}")

    def s_Yield(self, s):
        self.w(f"yield({self.x(s.value)})")

    def s_Break(self, s):
        self.w("break")

    def s_Continue(self, s):
        self.w("continue")

    def s_ExprStmt(self, s):
        self.w(self.x(s.expr))

    def s_Print(self, s):
        sep = self.x(s.sep) if s.sep is not None else '" "'
        end = self.x(s.end) if s.end is not None else '"\\n"'
        pre = ""
        if len(s.args) > 1 and any(not isinstance(a, (ir.Var, ir.Const)) for a in s.args[1:]):
            # Python évalue TOUS les arguments avant d'en convertir un en texte
            pre = "".join(f"val pyP{i} = {self.x(a)}; " for i, a in enumerate(s.args))
            parts = [f"pyP{i}" if a.type == STR else f"pyStr(pyP{i})" for i, a in enumerate(s.args)]
        else:
            parts = [self.x(a) if a.type == STR else f"pyStr({self.x(a)})" for a in s.args]
        body = f" + {sep} + ".join(parts) if parts else '""'
        call = f"{'System.err.print' if s.err else 'print'}({body} + {end})"
        self.w(f"run {{ {pre}{call} }}" if pre else call)

    # ---------- expressions ----------
    def lvalue(self, t):
        if isinstance(t, ir.Var):
            return self.var(t.name)
        if isinstance(t, ir.Attr):
            return self.x_Attr(t)
        b = self.x(t.base)
        if t.base.type.kind == "dict":
            return f"{b}[{self.x(t.index)}]"
        return f"{b}[{b}.pyIdx({self.x(t.index)})]"

    def x(self, e):
        return getattr(self, "x_" + type(e).__name__)(e)

    def x_Const(self, e):
        if e.type == INT:
            return f"{e.value}L"
        if e.type == FLOAT:
            r = repr(e.value)
            return r if any(c in r for c in ".eE") else r + ".0"
        if e.type == BOOL:
            return "true" if e.value else "false"
        if e.type == NONE:
            return "null"
        return kstr(e.value)

    def x_Var(self, e):
        if e.name == "self":
            # dans iterator { ... } (méthode génératrice), `this` désignerait le SequenceScope : on nomme la classe
            return f"this@{self.cname(self.cur_owner.name)}" if getattr(self, "in_gen", False) and self.cur_owner is not None else "this"
        return self.var(e.name)

    def x_Attr(self, e):
        return f"{self.x(e.obj)}.{self.var(e.name)}"

    def x_New(self, e):
        c = self.classes_by_name.get(e.cls)
        a = [self.x(v) for v in e.args]
        n = self.cname(e.cls)
        if c is None or not c.hier or (c.is_exc and c.init_owner is None):
            return f"{n}({', '.join(a)})"  # exception intégrée / à arguments libres / classe ordinaire
        if c.init_owner is None:
            return f"{n}()"
        init = f"it.pyInit{self.cname(c.init_owner)}"
        if c.is_exc:  # BaseException.__new__ range les arguments du constructeur dans .args avant __init__
            names = [f"pyA{i}" for i in range(len(a))]
            binds = "".join(f"val {nm} = {v}; " for nm, v in zip(names, a))
            return f"run {{ {binds}{n}().also {{ it.pySetArgs({', '.join(names)}); {init}({', '.join(names)}) }} }}"
        return f"{n}().also {{ {init}({', '.join(a)}) }}"

    def x_UserMethodCall(self, e):
        return f"{self.x(e.obj)}.{self.mname(e.name)}({', '.join(self.x(a) for a in e.args)})"

    def x_Comp(self, e):
        """Compréhension -> bloc `run { ... }` dont le corps réutilise les émetteurs d'instructions."""
        saved = (self.lines, self.ind)
        self.lines, self.ind = [], saved[1] + 1
        self.w(self.decl(e.result, e.type))
        self.stmts(e.body)
        self.w(self.var(e.result))
        inner = "\n".join(self.lines)
        self.lines, self.ind = saved
        return "run {\n" + inner + "\n" + "    " * saved[1] + "}"

    def x_BinOp(self, e):
        l, r = self.x(e.left), self.x(e.right)
        if e.type.kind == "list":
            return f"({l} + {r}).toMutableList()" if e.op == "+" else f"pyRepeat({l}, {r})"
        if e.op == "*" and e.type == STR:
            return f"pyRepeatStr({l}, {r})"
        if e.op in ("/", "/i"):
            return f"pyDiv({l}, {r})" if e.op == "/i" else f"pyFdiv({l}, {r})"
        if e.op == "//":
            return f"pyFloorDiv({l}, {r})"
        if e.op == "%":
            return f"pyFloorMod({l}, {r})"
        if e.op == "**":
            return f"ipow({l}, {r})" if e.type == INT else f"pyFpow({l}, {r})"
        if e.op in ("<<", ">>"):
            return f"{'pyShl' if e.op == '<<' else 'pyShr'}({l}, {r})"
        if e.type == INT and e.op in ("+", "-", "*"):  # arithmétique 64 bits vérifiée : dépassement -> OverflowError
            return f"{ {'+': 'pyAdd', '-': 'pySub', '*': 'pyMul'}[e.op] }({l}, {r})"
        if e.op in BIT:
            return f"({l} {BIT[e.op]} {r})"
        return f"({l} {e.op} {r})"

    def x_Cmp(self, e):
        l, r = self.x(e.left), self.x(e.right)
        if e.op in ("is", "isnot"):
            return f"({l} {'===' if e.op == 'is' else '!=='} {r})"
        if e.op == "in":
            return f"({l} in {r})"
        if e.op == "notin":
            return f"({l} !in {r})"
        return f"({l} {CMP[e.op]} {r})"

    def x_BoolOp(self, e):
        sym = " && " if e.op == "and" else " || "
        return "(" + sym.join(self.x(v) for v in e.values) + ")"

    def x_Unary(self, e):
        o = self.x(e.operand)
        if e.op == "~":
            return f"({o}).inv()"
        if e.op == "-" and e.type == INT:
            return f"pyNeg({o})"
        return f"({'!' if e.op == 'not' else e.op}{o})"

    def x_Ternary(self, e):
        return f"(if ({self.x(e.cond)}) {self.x(e.a)} else {self.x(e.b)})"

    def x_Cast(self, e):
        o, src, dst = self.x(e.operand), e.operand.type, e.type
        if src == INT and dst == FLOAT:
            return f"({o}).toDouble()"
        if src == FLOAT and dst == INT:
            return f"pyF2i({o})"
        if src == BOOL and dst == INT:
            return f"(if ({o}) 1L else 0L)"
        return f"(if ({o}) 1.0 else 0.0)"

    def x_Index(self, e):
        b, i = self.x(e.base), self.x(e.index)
        if e.base.type.kind == "dict":
            return f"pyDGet({b}, {i})"
        if e.base.type == STR:
            return f"{b}[{b}.pyIdx({i})].toString()"
        return f"{b}[{b}.pyIdx({i})]"

    def x_ListLit(self, e):
        lit = f"mutableListOf<{self.ty(e.type.args[0])}>({', '.join(self.x(v) for v in e.elems)})"
        return f"PyVTuple({lit})" if e.type.kind == "vtuple" else lit

    def x_DictLit(self, e):
        items = ", ".join(f"{self.x(k)} to {self.x(v)}" for k, v in zip(e.keys, e.values))
        return f"mutableMapOf<{self.ty(e.type.args[0])}, {self.ty(e.type.args[1])}>({items})"

    def x_KeyOp(self, e):
        lam = e.lam
        fn = f"{{ {self.var(lam.param)} -> {self.x(lam.body)} }}"
        xs = self.x(e.args[0])
        if e.kind == "min":
            return f"({xs}.minByOrNull {fn} ?: throw ValueError(\"min() arg is an empty sequence\"))"
        if e.kind == "max":
            return f"({xs}.maxByOrNull {fn} ?: throw ValueError(\"max() arg is an empty sequence\"))"
        return f"py{'Sorted' if e.kind == 'sorted' else 'Sort'}Key({xs}, {self.x(e.rev)}) {fn}"

    def x_LambdaVal(self, e):
        ps = ", ".join(f"{self.var(n)}: {self.ty(t)}" for n, t in e.params)
        return f"{{ {ps + ' -> ' if ps else ''}{self.x(e.body)} }}"

    def x_FuncRef(self, e):
        return f"::{self.var(e.name) if e.kind == 'local' else func_name(self.case(e.name), KOTLIN_RESERVED)}"

    def x_CallVal(self, e):
        return f"({self.x(e.fn)})({', '.join(self.x(a) for a in e.args)})"

    def x_SuperCall(self, e):
        a = ", ".join(self.x(v) for v in e.args)
        if e.name == "__init__":
            if e.owner is None:
                return f"pySetArgs({a})" if self.cur_owner is not None and self.cur_owner.is_exc else "Unit"
            return f"pyInit{self.cname(e.owner)}({a})"
        return f"super.{self.mname(e.name)}({a})"

    def x_IsInstance(self, e):
        x = self.x(e.operand)
        return "(" + " || ".join(f"{x} is {self.cname(c)}" for c in e.classes) + ")"

    def x_Downcast(self, e):
        return f"({self.x(e.operand)} as {self.cname(e.type.args[0])})"

    def x_DictNew(self, e):
        kt, vt = e.type.args
        d = self.default(vt) if e.mode != 3 else None
        mk = d if d is not None else '{ throw KeyError("") }'
        mk = "{ " + d + " }" if d is not None else mk
        return f'PyFlavDict<{self.ty(kt)}, {self.ty(vt)}>({e.mode}, {kstr(e.factory)}) {mk}'

    def x_NoneOf(self, e):
        return "null"

    def x_Wrap(self, e):
        return self.x(e.operand)

    def x_Unwrap(self, e):
        return f"{'pyNnAttr' if e.type.kind in ('class', 'list', 'dict') else 'pyNn'}({self.x(e.operand)})"

    def x_IsNone(self, e):
        return f"({self.x(e.operand)} {'!=' if e.negate else '=='} null)"

    def x_Slice(self, e):
        return f"pySlice({self.x(e.base)}, {self.bounds(e.lo, e.hi, e.step)})"

    def x_LibConst(self, e):
        return CONSTS[e.name][3]

    def x_TupleLit(self, e):
        return f"{self.ty(e.type)}({', '.join(self.x(v) for v in e.elems)})"

    def x_TupleGet(self, e):
        return f"{self.x(e.base)}.f{e.index}"

    def x_MethodCall(self, e):
        o = self.x(e.obj)
        if e.name == "keys":
            return f"{o}.keys.toMutableList()"
        if e.name == "values":
            return f"{o}.values.toMutableList()"
        if e.name == "items":
            return f"{o}.entries.map {{ {self.ty(e.type.args[0])}(it.key, it.value) }}.toMutableList()"
        if e.name == "get1":
            return f"{o}[{self.x(e.args[0])}]"
        if e.name == "pop" and e.obj.type.kind == "dict":
            return f"pyDPop({', '.join([o] + [self.x(a) for a in e.args])})"
        if e.name == "setdefault":
            return f"pySetdefault({o}, {self.x(e.args[0])}, {self.x(e.args[1])})"
        if e.name == "update":
            return f"pyDUpdate({o}, {self.x(e.args[0])})"
        if e.name == "copy":
            return f"pyDCopy({o})"
        if e.name == "clear":
            return f"{o}.clear()"
        if e.name == "popitem":
            return f"{o}.entries.last().let {{ pyE -> {o}.remove(pyE.key); {self.ty(e.type)}(pyE.key, pyE.value) }}"
        if e.name == "pop":
            return f"{o}.pyPop({self.x(e.args[0])})"
        if e.name == "extend":
            return f"{o}.addAll({self.x(e.args[0])}.toList())"
        if e.name in ("insert", "count", "index", "remove"):
            return f"{o}.py{e.name.capitalize()}({', '.join(self.x(a) for a in e.args)})"
        if e.name == "append":
            return f"{o}.add({self.x(e.args[0])})"
        if e.name in ("sort", "reverse"):
            return f"{o}.{e.name}()"
        return f"{o}.getOrDefault({self.x(e.args[0])}, {self.x(e.args[1])})"  # get

    def x_Call(self, e):
        a = [self.x(v) for v in e.args]
        if e.kind == "local":
            return f"{self.var(e.name)}({', '.join(a)})"
        if e.kind == "user":
            return f"{func_name(self.case(e.name), KOTLIN_RESERVED)}({', '.join(a)})"
        if e.kind == "lib":
            tpl = LOG[len(a)][1] if e.name == "math.log" else LIB[e.name].kt
            return tpl.format(*a)
        n = e.name
        if n == "vt_list":
            return f"{a[0]}.l"
        if n == "gen_list":
            return f"{a[0]}.asSequence().toMutableList()"
        if n == "prod":
            return f"pyProdI({a[0]})" if e.type == INT else f"{a[0]}.fold(1.0) {{ pyAcc, pyX -> pyAcc * pyX }}"
        if n in ("partition", "rpartition"):
            return f"py{n.capitalize()}({', '.join(a)}).let {{ Tup3(it.first, it.second, it.third) }}"
        if n in ("product2", "product3"):
            if n == "product2":
                return f"{a[0]}.flatMap {{ x -> {a[1]}.map {{ y -> Tup2(x, y) }} }}.toMutableList()"
            return f"{a[0]}.flatMap {{ x -> {a[1]}.flatMap {{ y -> {a[2]}.map {{ z -> Tup3(x, y, z) }} }} }}.toMutableList()"
        if n == "vt_to_tuples":
            k = len(e.type.args[0].args)
            return f"{a[0]}.map {{ Tup{k}({', '.join(f'it[{i}]' for i in range(k))}) }}.toMutableList()"
        if n == "join_star":
            return f"{a[0]}.joinToString({a[1]}) {{ pyStr(it) }}"
        if n == "type_name":
            c = self.classes_by_name.get(e.args[0].type.args[0])
            if c is not None and not c.hier:
                return kstr(c.name)
            return f"{a[0]}.pyName()"
        isint = "true" if e.type.kind == "set" and e.type.args[0] in (INT, BOOL) else "false"
        if n == "set_new":
            return f"PySet<{self.ty(e.type.args[0])}>({isint})"
        if n == "set_from":
            return f"pySetFromList({isint}, {a[0]})"
        if n in ("set_lit", "set_lit_folded"):
            return f"pySetLit({isint}, {a[0]}, {'true' if n == 'set_lit_folded' else 'false'})"
        if n == "deque_new":
            return f"PyDeque<{self.ty(e.type.args[0])}>({a[0]})"
        if n == "most_common":
            return f"pyMostCommon({a[0]}, {a[1]}).map {{ Tup2(it.first, it.second) }}.toMutableList()"
        if n == "popitem_at":
            return f"pyPopitemAt({a[0]}, {a[1]}).let {{ Tup2(it.first, it.second) }}"
        if n == "len":
            return f"{a[0]}.{'length' if e.args[0].type == STR else 'size'}.toLong()"
        if n == "abs":
            return f"pyAbs({a[0]})" if e.type == INT else f"Math.abs({a[0]})"
        if n == "str":
            return a[0] if e.args[0].type == STR else f"pyStr({a[0]})"
        if n in ("min", "max"):
            return f"{n}Of({', '.join(a)})"
        if n in ("min_list", "max_list"):
            return f"py{n[:3].capitalize()}List({a[0]})"
        if n == "sum":
            return f"pySumI({a[0]})" if e.type == INT else f"{a[0]}.sum()"
        if n == "list":
            return f"PyVTuple({a[0]}.toMutableList())" if e.type.kind == "vtuple" else f"{a[0]}.toMutableList()"
        if n in ("any", "all"):
            return f"{a[0]}.{n} {{ it }}"
        if n == "reversed":
            return f"{a[0]}.reversed().toMutableList()"
        if n == "enumerate":
            return f"{a[0]}.mapIndexed {{ pyI, pyX -> {self.ty(e.type.args[0])}(pyI.toLong() + {a[1]}, pyX) }}.toMutableList()"
        if n == "zip" and len(a) == 3:
            tt = self.ty(e.type.args[0])
            return f"run {{ val pyA = {a[0]}; val pyB = {a[1]}; val pyC = {a[2]}; (0 until minOf(pyA.size, pyB.size, pyC.size)).map {{ {tt}(pyA[it], pyB[it], pyC[it]) }}.toMutableList() }}"
        if n == "zip":
            return f"{a[0]}.zip({a[1]}).map {{ {self.ty(e.type.args[0])}(it.first, it.second) }}.toMutableList()"
        if n == "tuple_list":
            return f"{a[0]}.toL()"
        if n == "sum_start":
            return f"{a[0]}.fold({a[1]}) {{ pyAcc, pyX -> {'pyAdd(pyAcc, pyX)' if e.type == INT else 'pyAcc + pyX'} }}"
        if n == "sorted":
            return f"{a[0]}.sorted().toMutableList()"
        camel = "".join(p.capitalize() for p in n.split("_"))  # round_n -> pyRoundN, split_ws -> pySplitWs ...
        return f"py{camel}({', '.join(a)})"

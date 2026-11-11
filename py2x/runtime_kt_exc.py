"""Runtime Kotlin des exceptions : la hiérarchie de Python. `Exception` s'appelle PyException (kotlin.Exception existe déjà)."""
from .excs import BUILTIN_EXC


def kt_name(n):
    return "PyException" if n == "Exception" else n


def exc_runtime():
    L = ['''
// ---------- exceptions Python ----------
open class PyException(vararg a: Any?) : RuntimeException(), PyObj {
    var pyArgs: MutableList<Any?> = a.toMutableList()
    fun pySetArgs(vararg x: Any?) { pyArgs = x.toMutableList() }
    open fun pyName(): String = "Exception"
    open fun pyExcStr(): String = when (pyArgs.size) { 0 -> ""; 1 -> pyStr(pyArgs[0]); else -> pyArgs.joinToString(", ", "(", ")") { pyRepr(it) } }
    fun pyExcRepr(): String = pyName() + pyArgs.joinToString(", ", "(", ")") { pyRepr(it) }
    override fun pyStrObj(): String = pyExcStr()
    override fun pyReprObj(): String = pyExcRepr()
    override val message: String? get() = pyExcStr()
}''']
    for name, parent in BUILTIN_EXC.items():
        if parent is None:
            continue
        extra = ""
        if name == "KeyError":
            extra = " override fun pyExcStr(): String = if (pyArgs.size == 1) pyRepr(pyArgs[0]) else super.pyExcStr()"
        L.append(f"open class {name}(vararg a: Any?) : {kt_name(parent)}(*a) {{ override fun pyName(): String = \"{name}\";{extra} }}")
    return "\n".join(L) + "\n"


EXC_KT = exc_runtime()

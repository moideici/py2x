import re

CPP_RESERVED = set("""alignas alignof and and_eq asm auto bitand bitor bool break case catch char class compl concept const
consteval constexpr constinit const_cast continue co_await co_return co_yield decltype default delete do double
dynamic_cast else enum explicit export extern false float for friend goto if inline int long mutable namespace new
noexcept not not_eq nullptr operator or or_eq private protected public register reinterpret_cast requires return short
signed sizeof static static_assert static_cast struct switch template this thread_local throw true try typedef typeid
typename union unsigned using virtual void volatile wchar_t while xor xor_eq std main exit abort printf puts rand srand
time clock index NULL EOF""".split())

KOTLIN_RESERVED = set("""as break class continue do else false for fun if in interface is null object package return
super this throw true try typealias typeof val var when while by catch constructor delegate dynamic field file finally
get import init param property receiver set setparam value where abstract actual annotation companion const crossinline
data enum expect external final infix inline inner internal lateinit noinline open operator out override private
protected public reified sealed suspend tailrec vararg equals hashCode toString""".split())


def mangle(name, reserved):
    """Nom sûr dans la langue cible : évite mots-clés, `_` seul (réservé en Kotlin), préfixes du runtime."""
    if re.fullmatch(r"_+", name):
        return name + "v"
    if name in reserved or name.startswith("py_") or name.startswith("__"):
        return name + "_"
    return name


def func_name(name, reserved):
    """La fonction Python `main` devient py_main : le vrai point d'entrée est généré à part."""
    return "py_main" if name == "main" else mangle(name, reserved)

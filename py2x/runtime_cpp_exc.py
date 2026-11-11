"""Runtime C++ des exceptions : une hiérarchie de classes (comme en Python), levées via PyThrow, attrapées par type dynamique."""
from .excs import BUILTIN_EXC


def exc_runtime():
    L = [r'''
// ---------- exceptions Python ----------
struct BaseException : std::enable_shared_from_this<BaseException> {
    static constexpr bool py_value_eq = false;
    static constexpr bool py_has_eq = false;
    static constexpr bool py_has_lt = false;
    std::vector<std::string> a_str, a_repr;
    BaseException() = default;
    template <class... A> explicit BaseException(const A&... a) { py_set_args(a...); }
    template <class... A> void py_set_args(const A&... a) { a_str = std::vector<std::string>{py_str(a)...}; a_repr = std::vector<std::string>{py_repr(a)...}; }
    virtual ~BaseException() = default;
    virtual const char* py_name() const { return "BaseException"; }
    virtual std::string py_exc_str() const {
        if (a_str.empty()) return "";
        if (a_str.size() == 1) return a_str[0];
        std::string r = "(";
        for (size_t i = 0; i < a_repr.size(); i++) { if (i) r += ", "; r += a_repr[i]; }
        return r + ")";
    }
    std::string py_exc_repr() const {
        std::string r = std::string(py_name()) + "(";
        for (size_t i = 0; i < a_repr.size(); i++) { if (i) r += ", "; r += a_repr[i]; }
        return r + ")";
    }
};
struct PyThrow { std::shared_ptr<BaseException> p; };
''']
    for name, parent in BUILTIN_EXC.items():
        base = parent or "BaseException"
        extra = ""
        if name == "KeyError":
            extra = " std::string py_exc_str() const override { return a_repr.size() == 1 ? a_repr[0] : BaseException::py_exc_str(); }"
        L.append(f"struct {name} : {base} {{ using {base}::{base}; const char* py_name() const override {{ return \"{name}\"; }}{extra} }};")
        L.append(f"static inline std::string py_str(const std::shared_ptr<{name}>& p) {{ return p ? p->py_exc_str() : std::string(\"None\"); }}")
        L.append(f"static inline std::string py_repr(const std::shared_ptr<{name}>& p) {{ return p ? p->py_exc_repr() : std::string(\"None\"); }}")
    L.append("[[noreturn]] void py_throw(const char* type, const std::string& msg) {\n    std::string t = type;")
    L.append('    if (t == "KeyError") { auto k = std::make_shared<KeyError>(msg); k->a_repr[0] = msg; throw PyThrow{k}; }  // msg est déjà un repr de clé')
    for name in BUILTIN_EXC:
        L.append(f"    if (t == \"{name}\") throw PyThrow{{std::make_shared<{name}>(msg)}};")
    L.append("    throw PyThrow{std::make_shared<RuntimeError>(msg)};\n}")
    L.append(r'''template <class T> [[noreturn]] static inline void py_raise(const std::shared_ptr<T>& e) {
    if (!e) py_throw("TypeError", "exceptions must derive from BaseException");
    throw PyThrow{e};
}
template <class T> std::string py_repr_any(const T& x) { return py_repr(x); }
template <class T> static inline bool py_isinst(const PyThrow& t) { return std::dynamic_pointer_cast<T>(t.p) != nullptr; }
struct PyFinally {  // `finally` : s'exécute à toute sortie du bloc try (fin normale, return, break, continue, exception)
    std::function<void()> f;
    explicit PyFinally(std::function<void()> g) : f(std::move(g)) {}
    ~PyFinally() noexcept(false) { f(); }
};
''')
    return "\n".join(L)


EXC_CPP = exc_runtime()

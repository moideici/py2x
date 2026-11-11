"""Runtime C++ émis en tête de chaque programme généré : reproduit la sémantique de Python.

list et dict sont des POIGNÉES (shared_ptr) : copier la poignée = alias, exactement comme en Python (b = a partage la liste).
La copie explicite (list(x), x[:], x.copy()) fabrique une nouvelle liste.
"""

PRELUDE = r'''// --- runtime py2x : reproduit la sémantique de Python ---
#include <algorithm>
#include <charconv>
#include <coroutine>
#include <deque>
#include <functional>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

[[noreturn]] void py_throw(const char* type, const std::string& msg);  // levée d'une exception Python (définie avec la hiérarchie, en fin de runtime)
template <class T> std::string py_repr_any(const T& x);

// list Python : poignée partagée (alias à la copie)
template <class T> struct PyList {
    using value_type = T;
    std::shared_ptr<std::vector<T>> p;
    PyList() : p(std::make_shared<std::vector<T>>()) {}
    explicit PyList(std::vector<T> v) : p(std::make_shared<std::vector<T>>(std::move(v))) {}
    size_t size() const { return p->size(); }
    bool empty() const { return p->empty(); }
    auto begin() const { return p->begin(); }
    auto end() const { return p->end(); }
    decltype(auto) operator[](size_t i) const { return (*p)[i]; }
    template <class... A> void push_back(A&&... a) const { p->push_back(std::forward<A>(a)...); }
    template <class... A> auto insert(A&&... a) const { return p->insert(std::forward<A>(a)...); }
    template <class... A> auto erase(A&&... a) const { return p->erase(std::forward<A>(a)...); }
};

template <class T> bool operator<(const PyList<T>& a, const PyList<T>& b) {  // tri de tuples contenant des listes (comparaison lexicographique)
    return std::lexicographical_compare(a.begin(), a.end(), b.begin(), b.end());
}

// tuple de longueur variable (tuple[T, ...], lignes de zip(*m), résultats d'itertools) : même représentation qu'une liste, affichage de tuple
template <class T> struct PyVT : PyList<T> {
    PyVT() : PyList<T>() {}
    PyVT(const PyList<T>& l) : PyList<T>(l) {}
    explicit PyVT(std::vector<T> v) : PyList<T>(std::move(v)) {}
};
template <class T> static inline PyList<T> py_vt_list(const PyVT<T>& v) { return static_cast<const PyList<T>&>(v); }

// dict Python : poignée partagée, ordre d'insertion conservé
template <class K, class V> struct PyDictImpl {
    std::vector<std::pair<K, V>> e;
    std::map<K, size_t> idx;
    int mode = 0;  // 0 dict, 1 defaultdict (lire une clé absente l'insère), 2 Counter (lire une clé absente donne 0), 3 OrderedDict
    std::string fname;
    V dflt{};
    V& operator[](const K& k) {
        auto it = idx.find(k);
        if (it != idx.end()) return e[it->second].second;
        idx[k] = e.size();
        e.emplace_back(k, V{});
        return e.back().second;
    }
    V& at(const K& k) {
        auto it = idx.find(k);
        if (it == idx.end()) {
            if (mode == 1) return (*this)[k];
            if (mode == 2) { dflt = V{}; return dflt; }
            py_throw("KeyError", py_repr_any(k));
        }
        return e[it->second].second;
    }
    void erase(const K& k) {
        auto it = idx.find(k);
        if (it == idx.end()) py_throw("KeyError", py_repr_any(k));
        size_t i = it->second;
        idx.erase(it);
        e.erase(e.begin() + i);
        for (size_t j = i; j < e.size(); j++) idx[e[j].first] = j;
    }
};
template <class K, class V> struct PyDict {
    using key_type = K;
    using mapped_type = V;
    std::shared_ptr<PyDictImpl<K, V>> p;
    PyDict() : p(std::make_shared<PyDictImpl<K, V>>()) {}
    PyDict(std::initializer_list<std::pair<K, V>> init) : PyDict() { for (const auto& kv : init) (*p)[kv.first] = kv.second; }
    V& operator[](const K& k) const { return (*p)[k]; }
    V& at(const K& k) const { return p->at(k); }
    size_t size() const { return p->e.size(); }
    size_t count(const K& k) const { return p->idx.count(k); }
    void erase(const K& k) const { p->erase(k); }
    void clear() const { p->e.clear(); p->idx.clear(); }
    auto begin() const { return p->e.begin(); }
    auto end() const { return p->e.end(); }
};

// égalité à la Python : par VALEUR pour list/dict/tuple/dataclass, par IDENTITÉ pour les autres objets
template <class T> bool py_eq(const T& a, const T& b);
template <class T> bool py_eq(const PyList<T>& a, const PyList<T>& b);
template <class K, class V> bool py_eq(const PyDict<K, V>& a, const PyDict<K, V>& b);
template <class... Ts> bool py_eq(const std::tuple<Ts...>& a, const std::tuple<Ts...>& b);
template <class T> bool py_eq(const std::shared_ptr<T>& a, const std::shared_ptr<T>& b);
template <class T> bool py_eq(const std::optional<T>& a, const std::optional<T>& b);
template <class T> bool py_eq(const T& a, const T& b) { return a == b; }
template <class T> bool py_eq(const PyList<T>& a, const PyList<T>& b) {
    if (a.size() != b.size()) return false;
    for (size_t i = 0; i < a.size(); i++) if (!py_eq(a[i], b[i])) return false;
    return true;
}
template <class K, class V> bool py_eq(const PyDict<K, V>& a, const PyDict<K, V>& b) {
    if (a.size() != b.size()) return false;
    for (const auto& kv : a) if (!b.count(kv.first) || !py_eq(b.at(kv.first), kv.second)) return false;
    return true;
}
template <class Tup, size_t... I> bool py_eq_tuple(const Tup& a, const Tup& b, std::index_sequence<I...>) {
    return (py_eq(std::get<I>(a), std::get<I>(b)) && ...);
}
template <class... Ts> bool py_eq(const std::tuple<Ts...>& a, const std::tuple<Ts...>& b) {
    return py_eq_tuple(a, b, std::index_sequence_for<Ts...>{});
}
template <class T> requires (T::py_has_lt) bool operator<(const std::shared_ptr<T>& a, const std::shared_ptr<T>& b) { return a->py_op_lt(b); }
template <class T> bool py_eq(const std::shared_ptr<T>& a, const std::shared_ptr<T>& b) {
    if (!a || !b) return a == b;  // None == None est vrai, None == objet est faux
    if constexpr (T::py_has_eq) return a->py_op_eq(b);
    else if constexpr (T::py_value_eq) return a->py_eq_fields(*b);
    else return a == b;
}
template <class T> bool py_eq(const std::optional<T>& a, const std::optional<T>& b) {
    if (!a || !b) return a.has_value() == b.has_value();
    return py_eq(*a, *b);
}

static inline std::string py_str(long long);
static inline std::string py_str(bool);
static inline std::string py_str(double);
static inline std::string py_str(const std::string&);
template <class T> std::string py_str(const PyList<T>&);
template <class K, class V> std::string py_str(const PyDict<K, V>&);
template <class T> std::string py_str(const PyVT<T>&);
template <class... Ts> std::string py_str(const std::tuple<Ts...>&);
template <class T> std::string py_str(const std::optional<T>&);
template <class T> std::string py_repr(const std::optional<T>&);
template <class T> std::string py_str(const std::shared_ptr<T>& p) { return p ? std::string("<object>") : std::string("None"); }  // objet sans __str__/__repr__ (repli ; les classes affichables ont leur propre surcharge)
static inline std::string py_repr(const std::string& s) {  // règle de Python : guillemets doubles si la chaîne contient ' sans "
    char q = (s.find('\'') != std::string::npos && s.find('"') == std::string::npos) ? '"' : '\'';
    std::string r(1, q);
    for (unsigned char c : s) {
        if (c == '\\') r += "\\\\";
        else if (c == (unsigned char)q) { r += '\\'; r += (char)c; }
        else if (c == '\n') r += "\\n";
        else if (c == '\t') r += "\\t";
        else if (c == '\r') r += "\\r";
        else if (c < 32 || c == 127) { char b[8]; std::snprintf(b, sizeof b, "\\x%02x", c); r += b; }
        else r += (char)c;
    }
    r += q;
    return r;
}
template <class T> std::string py_repr(const T& x) { return py_str(x); }

static inline std::string py_str(long long x) { return std::to_string(x); }
static inline std::string py_str(bool x) { return x ? "True" : "False"; }
static inline std::string py_str(double x) {  // repr() de Python : notation scientifique seulement si exposant < -4 ou >= 16
    if (std::isnan(x)) return "nan";
    if (std::isinf(x)) return x < 0 ? "-inf" : "inf";
    if (x == 0) return std::signbit(x) ? "-0.0" : "0.0";
    char buf[64];
    auto r = std::to_chars(buf, buf + 64, x, std::chars_format::scientific);
    std::string s(buf, r.ptr);
    bool neg = s[0] == '-';
    if (neg) s = s.substr(1);
    size_t epos = s.find('e');
    int e = std::atoi(s.c_str() + epos + 1);
    std::string digits;
    for (size_t i = 0; i < epos; i++) if (s[i] != '.') digits += s[i];
    std::string out;
    if (-4 <= e && e < 16) {
        if (e >= 0) {
            if ((int)digits.size() <= e + 1) out = digits + std::string((size_t)(e + 1) - digits.size(), '0') + ".0";
            else out = digits.substr(0, (size_t)e + 1) + "." + digits.substr((size_t)e + 1);
        } else out = "0." + std::string((size_t)(-e - 1), '0') + digits;
    } else {
        out = digits.substr(0, 1) + (digits.size() > 1 ? "." + digits.substr(1) : std::string()) + "e" + (e < 0 ? "-" : "+") +
              (std::abs(e) < 10 ? "0" : "") + std::to_string(std::abs(e));
    }
    return (neg ? "-" : "") + out;
}
static inline std::string py_str(const std::string& x) { return x; }
template <class T> std::string py_str(const PyList<T>& v) {
    std::string r = "[";
    for (size_t i = 0; i < v.size(); i++) { if (i) r += ", "; r += py_repr(v[i]); }
    return r + "]";
}
template <class K> static inline std::string py_counter_repr(const PyDict<K, long long>& d);
template <class K, class V> std::string py_str(const PyDict<K, V>& m) {
    if (m.p->mode == 2) { if constexpr (std::is_same<V, long long>::value) return py_counter_repr(m); }
    if (m.p->mode == 3) {
        if (m.size() == 0) return "OrderedDict()";
        std::string o = "OrderedDict([";
        bool f1 = true;
        for (const auto& kv : m) { if (!f1) o += ", "; f1 = false; o += "(" + py_repr(kv.first) + ", " + py_repr(kv.second) + ")"; }
        return o + "])";
    }
    std::string r = "{";
    bool first = true;
    for (const auto& kv : m) { if (!first) r += ", "; first = false; r += py_repr(kv.first) + ": " + py_repr(kv.second); }
    r += "}";
    return m.p->mode == 1 ? "defaultdict(" + m.p->fname + ", " + r + ")" : r;
}
template <class K, class V> static inline PyDict<K, V> py_dnew(int mode, const char* fname) {
    PyDict<K, V> d;
    d.p->mode = mode;
    d.p->fname = fname;
    return d;
}
template <class T> std::string py_str(const PyVT<T>& v) {
    std::string r = "(";
    for (size_t i = 0; i < v.size(); i++) { if (i) r += ", "; r += py_repr(v[i]); }
    if (v.size() == 1) r += ",";
    return r + ")";
}
template <class T> bool py_eq(const PyVT<T>& a, const PyVT<T>& b) {
    if (a.size() != b.size()) return false;
    for (size_t i = 0; i < a.size(); i++) if (!py_eq(a[i], b[i])) return false;
    return true;
}
template <class... Ts> std::string py_str(const std::tuple<Ts...>& t) {
    std::string r = "(";
    size_t i = 0;
    std::apply([&](const auto&... xs) { ((r += (i++ ? ", " : "") + py_repr(xs)), ...); }, t);
    if (sizeof...(Ts) == 1) r += ",";
    return r + ")";
}

template <class T> std::string py_str(const std::optional<T>& o) { return o ? py_str(*o) : std::string("None"); }
template <class T> std::string py_repr(const std::optional<T>& o) { return o ? py_repr(*o) : std::string("None"); }
template <class T> static inline std::shared_ptr<T> py_nn(const std::shared_ptr<T>& p) {
    if (!p) py_throw("AttributeError", "'NoneType' object has no attribute");
    return p;
}
template <class T> static inline T py_val(const std::optional<T>& o) {
    if (!o) py_throw("TypeError", "opération non supportée sur None");
    return *o;
}
template <class K, class V> static inline std::optional<V> py_get1(const PyDict<K, V>& m, const K& k) {
    if (m.count(k)) return m.at(k);
    return std::nullopt;
}
static inline double py_div(double a, double b) { if (b == 0.0) py_throw("ZeroDivisionError", "division by zero"); return a / b; }
static inline double py_fdiv(double a, double b) { if (b == 0.0) py_throw("ZeroDivisionError", "float division by zero"); return a / b; }
static inline long long py_range_step(long long s) {
    if (s == 0) py_throw("ValueError", "range() arg 3 must not be zero");
    return s;
}
static inline long long py_add(long long a, long long b) { long long r; if (__builtin_add_overflow(a, b, &r)) py_throw("OverflowError", "int too large: the translation uses 64-bit integers"); return r; }
static inline long long py_sub(long long a, long long b) { long long r; if (__builtin_sub_overflow(a, b, &r)) py_throw("OverflowError", "int too large: the translation uses 64-bit integers"); return r; }
static inline long long py_mul(long long a, long long b) { long long r; if (__builtin_mul_overflow(a, b, &r)) py_throw("OverflowError", "int too large: the translation uses 64-bit integers"); return r; }
static inline long long py_neg(long long a) { if (a == std::numeric_limits<long long>::min()) py_throw("OverflowError", "int too large: the translation uses 64-bit integers"); return -a; }
static inline long long py_iabs(long long a) { return a < 0 ? py_neg(a) : a; }
static inline long long py_shl(long long a, long long b) {
    if (b < 0) py_throw("ValueError", "negative shift count");
    if (a == 0) return 0;
    if (b >= 63) py_throw("OverflowError", "int too large: the translation uses 64-bit integers");
    long long r = (long long)((unsigned long long)a << b);
    if ((r >> b) != a) py_throw("OverflowError", "int too large: the translation uses 64-bit integers");
    return r;
}
static inline long long py_shr(long long a, long long b) {
    if (b < 0) py_throw("ValueError", "negative shift count");
    return b >= 63 ? (a < 0 ? -1 : 0) : (a >> b);
}
static inline long long py_floordiv(long long a, long long b) {
    if (b == 0) py_throw("ZeroDivisionError", "integer division or modulo by zero");
    long long q = a / b;
    if ((a % b != 0) && ((a < 0) != (b < 0))) q--;
    return q;
}
static inline long long py_mod(long long a, long long b) {
    if (b == 0) py_throw("ZeroDivisionError", "integer division or modulo by zero");
    long long r = a % b;
    if (r != 0 && ((r < 0) != (b < 0))) r += b;
    return r;
}
static inline long long py_pow(long long a, long long b) {
    if (b < 0) py_throw("ValueError", "negative exponent");
    long long r = 1;
    while (b) { if (b & 1) r = py_mul(r, a); b >>= 1; if (b) a = py_mul(a, a); }
    return r;
}
template <class V> static inline decltype(auto) py_at(V&& v, long long i) {  // decltype(auto) : vector<bool> renvoie un proxy
    long long n = (long long)v.size();
    if (i < 0) i += n;
    if (i < 0 || i >= n) {
        if constexpr (std::is_same<std::decay_t<V>, std::string>::value) py_throw("IndexError", "string index out of range");
        else py_throw("IndexError", "list index out of range");
    }
    return v[i];
}
template <class C, class X> static inline bool py_in(const C& c, const X& x) {
    for (const auto& e : c) if (py_eq(e, x)) return true;
    return false;
}
template <class K, class V, class X> static inline bool py_in(const PyDict<K, V>& m, const X& x) { return m.count(x) > 0; }
template <class K, class V, class D> static inline V py_get(const PyDict<K, V>& m, const K& k, const D& d) {
    return m.count(k) ? m.at(k) : (V)d;
}
template <class K, class V> static inline PyList<K> py_keys(const PyDict<K, V>& m) {
    std::vector<K> r; for (const auto& kv : m) r.push_back(kv.first); return PyList<K>(std::move(r));
}
template <class K, class V> static inline PyList<V> py_values(const PyDict<K, V>& m) {
    std::vector<V> r; for (const auto& kv : m) r.push_back(kv.second); return PyList<V>(std::move(r));
}
template <class K, class V> static inline PyList<std::tuple<K, V>> py_items(const PyDict<K, V>& m) {
    std::vector<std::tuple<K, V>> r; for (const auto& kv : m) r.emplace_back(kv.first, kv.second); return PyList<std::tuple<K, V>>(std::move(r));
}
static inline long long py_gcd(long long a, long long b) {
    a = a < 0 ? -a : a; b = b < 0 ? -b : b;
    while (b) { long long t = a % b; a = b; b = t; }
    return a;
}
static inline long long py_lcm(long long a, long long b) { return (a == 0 || b == 0) ? 0 : py_iabs(py_mul(a / py_gcd(a, b), b)); }
static inline long long py_isqrt(long long n) {
    if (n < 0) py_throw("ValueError", "isqrt() argument must be nonnegative");
    long long r = (long long)std::sqrt((double)n);
    while (r * r > n) r--;
    while ((r + 1) * (r + 1) <= n) r++;
    return r;
}
static inline long long py_factorial(long long n) {
    if (n < 0) py_throw("ValueError", "factorial() not defined for negative values");
    long long r = 1;
    for (long long i = 2; i <= n; i++) r = py_mul(r, i);
    return r;
}
template <class K, class V, class D> static inline V py_dpop(const PyDict<K, V>& m, const K& k, const D& d) {
    if (!m.count(k)) return (V)d;
    V v = m.at(k);
    m.erase(k);
    return v;
}
template <class K, class V> static inline V py_dpop(const PyDict<K, V>& m, const K& k) {
    V v = m.at(k);  // KeyError si absente
    m.erase(k);
    return v;
}
template <class K, class V> static inline V py_setdefault(const PyDict<K, V>& m, const K& k, const V& d) {
    if (!m.count(k)) m[k] = d;
    return m.at(k);
}
template <class K, class V> static inline void py_dupdate(const PyDict<K, V>& m, const PyDict<K, V>& o) {
    std::vector<std::pair<K, V>> t(o.begin(), o.end());
    for (auto& kv : t) {
        if constexpr (std::is_same<V, long long>::value) { if (m.p->mode == 2) { m[kv.first] += kv.second; continue; } }
        m[kv.first] = kv.second;
    }
}
template <class K, class V> static inline PyDict<K, V> py_dcopy(const PyDict<K, V>& m) {
    PyDict<K, V> r;
    r.p->mode = m.p->mode;
    r.p->fname = m.p->fname;
    for (const auto& kv : m) r[kv.first] = kv.second;
    return r;
}
template <class K, class V> static inline void py_dclear(const PyDict<K, V>& m) { m.clear(); }
template <class K, class V> static inline std::tuple<K, V> py_popitem(const PyDict<K, V>& m) {
    if (m.size() == 0) py_throw("KeyError", "'popitem(): dictionary is empty'");
    auto it = m.end();
    --it;
    std::pair<K, V> kv = *it;
    m.erase(kv.first);
    return std::tuple<K, V>(kv.first, kv.second);
}
template <class T> static inline void py_lclear(const PyList<T>& v) { v.erase(v.begin(), v.end()); }
template <class... Ts> static inline auto py_tuple_list(const std::tuple<Ts...>& t) {
    using T = std::tuple_element_t<0, std::tuple<Ts...>>;
    std::vector<T> r;
    std::apply([&](const auto&... xs) { (r.push_back(xs), ...); }, t);
    return PyList<T>(std::move(r));
}
template <class V, class S> static inline S py_sum_start(const V& v, S s) {
    for (const auto& x : v) { if constexpr (std::is_same<S, long long>::value) s = py_add(s, x); else s += x; }
    return s;
}
template <class T> static inline PyList<T> py_list(const PyList<T>& v) { return PyList<T>(std::vector<T>(v.begin(), v.end())); }
template <class T> static inline PyList<T> py_concat(const PyList<T>& a, const PyList<T>& b) {
    std::vector<T> r(a.begin(), a.end());
    r.insert(r.end(), b.begin(), b.end());
    return PyList<T>(std::move(r));
}
template <class T> static inline PyList<T> py_repeat(const PyList<T>& v, long long n) {
    std::vector<T> r;
    for (long long i = 0; i < n; i++) r.insert(r.end(), v.begin(), v.end());
    return PyList<T>(std::move(r));
}
static inline std::string py_repeat_str(const std::string& s, long long n) {
    std::string r;
    for (long long i = 0; i < n; i++) r += s;
    return r;
}
template <class V> static inline bool py_any(const V& v) { for (const auto& x : v) if (x) return true; return false; }
template <class V> static inline bool py_all(const V& v) { for (const auto& x : v) if (!x) return false; return true; }
template <class T> static inline PyList<std::tuple<long long, T>> py_enumerate(const PyList<T>& v, long long start) {
    std::vector<std::tuple<long long, T>> r;
    long long i = start;
    for (const auto& x : v) r.emplace_back(i++, x);
    return PyList<std::tuple<long long, T>>(std::move(r));
}
template <class A, class B> static inline PyList<std::tuple<A, B>> py_zip(const PyList<A>& a, const PyList<B>& b) {
    std::vector<std::tuple<A, B>> r;
    size_t n = std::min(a.size(), b.size());
    for (size_t i = 0; i < n; i++) r.emplace_back(a[i], b[i]);
    return PyList<std::tuple<A, B>>(std::move(r));
}
template <class A, class B, class C> static inline PyList<std::tuple<A, B, C>> py_zip(const PyList<A>& a, const PyList<B>& b, const PyList<C>& c) {
    std::vector<std::tuple<A, B, C>> r;
    size_t n = std::min(std::min(a.size(), b.size()), c.size());
    for (size_t i = 0; i < n; i++) r.emplace_back(a[i], b[i], c[i]);
    return PyList<std::tuple<A, B, C>>(std::move(r));
}
template <class T> static inline PyList<T> py_reversed(const PyList<T>& v) {
    std::vector<T> r(v.begin(), v.end());
    std::reverse(r.begin(), r.end());
    return PyList<T>(std::move(r));
}
template <class T> static inline T py_pop(const PyList<T>& v, long long i) {
    long long n = (long long)v.size();
    if (n == 0) py_throw("IndexError", "pop from empty list");
    if (i < 0) i += n;
    if (i < 0 || i >= n) py_throw("IndexError", "pop index out of range");
    T x = v[i];
    v.erase(v.begin() + i);
    return x;
}
template <class T> static inline void py_extend(const PyList<T>& v, const PyList<T>& w) {
    std::vector<T> t(w.begin(), w.end());  // copie d'abord : xs.extend(xs) est valide
    v.insert(v.end(), t.begin(), t.end());
}
template <class T, class X> static inline void py_insert(const PyList<T>& v, long long i, const X& x) {
    long long n = (long long)v.size();
    if (i < 0) { i += n; if (i < 0) i = 0; }
    if (i > n) i = n;
    v.insert(v.begin() + i, x);
}
template <class V, class X> static inline long long py_count(const V& v, const X& x) {
    long long c = 0;
    for (const auto& e : v) if (py_eq(e, x)) c++;
    return c;
}
template <class V, class X> static inline long long py_index(const V& v, const X& x) {
    for (size_t i = 0; i < v.size(); i++) if (py_eq(v[i], x)) return (long long)i;
    py_throw("ValueError", py_repr_any(x) + " is not in list");
}
template <class T, class X> static inline void py_remove(const PyList<T>& v, const X& x) {
    for (size_t i = 0; i < v.size(); i++) if (py_eq(v[i], x)) { v.erase(v.begin() + i); return; }
    py_throw("ValueError", "list.remove(x): x not in list");
}
template <class T, class F> static inline std::vector<size_t> py_key_order(const PyList<T>& v, F key, bool rev) {
    using K = decltype(key(std::declval<const T&>()));
    std::vector<std::pair<K, size_t>> kv;
    for (size_t i = 0; i < v.size(); i++) kv.emplace_back(key(v[i]), i);
    std::stable_sort(kv.begin(), kv.end(), [&](const auto& a, const auto& b) { return rev ? (b.first < a.first) : (a.first < b.first); });
    std::vector<size_t> idx;
    for (auto& p : kv) idx.push_back(p.second);
    return idx;
}
template <class T, class F> static inline PyList<T> py_sorted_key(const PyList<T>& v, F key, bool rev) {
    std::vector<T> r;
    for (size_t i : py_key_order(v, key, rev)) r.push_back(v[i]);
    return PyList<T>(std::move(r));
}
template <class T, class F> static inline void py_sort_key(const PyList<T>& v, F key, bool rev) {
    std::vector<T> r;
    for (size_t i : py_key_order(v, key, rev)) r.push_back(v[i]);
    std::copy(r.begin(), r.end(), v.begin());
}
template <class T, class F> static inline T py_min_key(const PyList<T>& v, F key) {
    if (v.empty()) py_throw("ValueError", "min() arg is an empty sequence");
    size_t best = 0;
    auto bk = key(v[0]);
    for (size_t i = 1; i < v.size(); i++) { auto k = key(v[i]); if (k < bk) { bk = k; best = i; } }
    return v[best];
}
template <class T, class F> static inline T py_max_key(const PyList<T>& v, F key) {
    if (v.empty()) py_throw("ValueError", "max() arg is an empty sequence");
    size_t best = 0;
    auto bk = key(v[0]);
    for (size_t i = 1; i < v.size(); i++) { auto k = key(v[i]); if (bk < k) { bk = k; best = i; } }
    return v[best];
}
template <class V> static inline auto py_min_list(const V& v) {
    if (v.empty()) py_throw("ValueError", "min() arg is an empty sequence");
    return *std::min_element(v.begin(), v.end());
}
template <class V> static inline auto py_max_list(const V& v) {
    if (v.empty()) py_throw("ValueError", "max() arg is an empty sequence");
    return *std::max_element(v.begin(), v.end());
}
template <class V> static inline auto py_sum(const V& v) {
    typename V::value_type s{};
    for (const auto& x : v) { if constexpr (std::is_same<typename V::value_type, long long>::value) s = py_add(s, x); else s += x; }
    return s;
}
template <class T> static inline PyList<T> py_sorted(const PyList<T>& v) {
    std::vector<T> r(v.begin(), v.end());
    std::sort(r.begin(), r.end());
    return PyList<T>(std::move(r));
}
// --- fin du runtime ---
'''

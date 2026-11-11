"""Runtime C++ : chaînes (ASCII), formatage (mini-langage de format de Python), conversions, tranches."""

STRINGS = r'''
// ---------- chaînes : sémantique de Python sur de l'ASCII ----------
static inline bool py_ws(char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\v' || c == '\f'; }
static inline bool py_alpha(char c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'); }
static inline bool py_digit(char c) { return c >= '0' && c <= '9'; }
static inline std::string py_upper(const std::string& s) { std::string r = s; for (auto& c : r) if (c >= 'a' && c <= 'z') c -= 32; return r; }
static inline std::string py_lower(const std::string& s) { std::string r = s; for (auto& c : r) if (c >= 'A' && c <= 'Z') c += 32; return r; }
static inline std::string py_swapcase(const std::string& s) {
    std::string r = s;
    for (auto& c : r) { if (c >= 'a' && c <= 'z') c -= 32; else if (c >= 'A' && c <= 'Z') c += 32; }
    return r;
}
static inline std::string py_capitalize(const std::string& s) {
    std::string r = py_lower(s);
    if (!r.empty() && r[0] >= 'a' && r[0] <= 'z') r[0] -= 32;
    return r;
}
static inline std::string py_title(const std::string& s) {
    std::string r = s;
    bool start = true;
    for (auto& c : r) {
        if (py_alpha(c)) { if (start) { if (c >= 'a' && c <= 'z') c -= 32; } else if (c >= 'A' && c <= 'Z') c += 32; start = false; }
        else start = true;
    }
    return r;
}
static inline std::string py_strip(const std::string& s, const std::string& chars, int mode) {  // mode 0 = both, 1 = left, 2 = right
    size_t a = 0, b = s.size();
    if (mode != 2) while (a < b && chars.find(s[a]) != std::string::npos) a++;
    if (mode != 1) while (b > a && chars.find(s[b - 1]) != std::string::npos) b--;
    return s.substr(a, b - a);
}
static inline PyList<std::string> py_split_ws(const std::string& s) {
    std::vector<std::string> r;
    size_t i = 0, n = s.size();
    while (i < n) {
        while (i < n && py_ws(s[i])) i++;
        if (i >= n) break;
        size_t j = i;
        while (j < n && !py_ws(s[j])) j++;
        r.push_back(s.substr(i, j - i));
        i = j;
    }
    return PyList<std::string>(std::move(r));
}
static inline PyList<std::string> py_split(const std::string& s, const std::string& sep, long long maxsplit) {
    if (sep.empty()) py_throw("ValueError", "empty separator");
    std::vector<std::string> r;
    size_t pos = 0;
    long long cnt = 0;
    while (maxsplit < 0 || cnt < maxsplit) {
        size_t f = s.find(sep, pos);
        if (f == std::string::npos) break;
        r.push_back(s.substr(pos, f - pos));
        pos = f + sep.size();
        cnt++;
    }
    r.push_back(s.substr(pos));
    return PyList<std::string>(std::move(r));
}
static inline PyList<std::string> py_rsplit(const std::string& s, const std::string& sep, long long maxsplit) {
    if (sep.empty()) py_throw("ValueError", "empty separator");
    std::vector<std::string> result;
    size_t end = s.size();
    long long count = 0;
    while (end >= sep.size() && (maxsplit < 0 || count < maxsplit)) {
        const size_t found = s.rfind(sep, end - sep.size());
        if (found == std::string::npos) break;
        result.push_back(s.substr(found + sep.size(), end - found - sep.size()));
        end = found;
        ++count;
    }
    result.push_back(s.substr(0, end));
    std::reverse(result.begin(), result.end());
    return PyList<std::string>(std::move(result));
}
static inline PyList<std::string> py_rsplit_ws(const std::string& s, long long maxsplit) {
    std::vector<std::string> result;
    size_t end = s.size();
    long long count = 0;
    while (end > 0 && py_ws(s[end - 1])) --end;
    while (end > 0) {
        if (maxsplit >= 0 && count >= maxsplit) {
            result.push_back(s.substr(0, end));
            break;
        }
        size_t start = end;
        while (start > 0 && !py_ws(s[start - 1])) --start;
        result.push_back(s.substr(start, end - start));
        end = start;
        while (end > 0 && py_ws(s[end - 1])) --end;
        ++count;
    }
    std::reverse(result.begin(), result.end());
    return PyList<std::string>(std::move(result));
}
static inline PyList<std::string> py_splitlines(const std::string& s) {
    std::vector<std::string> r;
    size_t i = 0, n = s.size();
    while (i < n) {
        size_t j = i;
        while (j < n && s[j] != '\n' && s[j] != '\r') j++;
        r.push_back(s.substr(i, j - i));
        if (j < n && s[j] == '\r' && j + 1 < n && s[j + 1] == '\n') j++;
        i = j + 1;
    }
    return PyList<std::string>(std::move(r));
}
static inline std::string py_join(const std::string& sep, const PyList<std::string>& xs) {
    std::string r;
    for (size_t i = 0; i < xs.size(); i++) { if (i) r += sep; r += xs[i]; }
    return r;
}
static inline std::string py_replace(const std::string& s, const std::string& from, const std::string& to, long long count) {
    std::string r;
    long long done = 0;
    if (from.empty()) {  // Python insère `to` entre chaque caractère (et aux deux bouts)
        for (size_t i = 0; i <= s.size(); i++) {
            if (count < 0 || done < count) { r += to; done++; }
            if (i < s.size()) r += s[i];
        }
        return r;
    }
    size_t pos = 0;
    while (count < 0 || done < count) {
        size_t f = s.find(from, pos);
        if (f == std::string::npos) break;
        r.append(s, pos, f - pos);
        r += to;
        pos = f + from.size();
        done++;
    }
    r.append(s, pos, std::string::npos);
    return r;
}
static inline bool py_startswith(const std::string& s, const std::string& p) { return s.size() >= p.size() && s.compare(0, p.size(), p) == 0; }
static inline bool py_endswith(const std::string& s, const std::string& p) { return s.size() >= p.size() && s.compare(s.size() - p.size(), p.size(), p) == 0; }
static inline long long py_find(const std::string& s, const std::string& sub) {
    size_t f = s.find(sub);
    return f == std::string::npos ? -1 : (long long)f;
}
static inline long long py_rfind(const std::string& s, const std::string& sub) {
    size_t f = s.rfind(sub);
    return f == std::string::npos ? -1 : (long long)f;
}
static inline long long py_sindex(const std::string& s, const std::string& sub) {
    long long f = py_find(s, sub);
    if (f < 0) py_throw("ValueError", "substring not found");
    return f;
}
static inline long long py_scount(const std::string& s, const std::string& sub) {
    if (sub.empty()) return (long long)s.size() + 1;
    long long c = 0;
    size_t pos = 0;
    while ((pos = s.find(sub, pos)) != std::string::npos) { c++; pos += sub.size(); }
    return c;
}
template <class F> static inline bool py_all_chars(const std::string& s, F f) {
    if (s.empty()) return false;
    for (char c : s) if (!f(c)) return false;
    return true;
}
static inline bool py_isdigit(const std::string& s) { return py_all_chars(s, py_digit); }
static inline bool py_isalpha(const std::string& s) { return py_all_chars(s, py_alpha); }
static inline bool py_isalnum(const std::string& s) { return py_all_chars(s, [](char c) { return py_alpha(c) || py_digit(c); }); }
static inline bool py_isspace(const std::string& s) { return py_all_chars(s, py_ws); }
static inline bool py_islower(const std::string& s) {
    bool any = false;
    for (char c : s) { if (c >= 'A' && c <= 'Z') return false; if (c >= 'a' && c <= 'z') any = true; }
    return any;
}
static inline bool py_isupper(const std::string& s) {
    bool any = false;
    for (char c : s) { if (c >= 'a' && c <= 'z') return false; if (c >= 'A' && c <= 'Z') any = true; }
    return any;
}
static inline std::string py_zfill(const std::string& s, long long w) {
    if ((long long)s.size() >= w) return s;
    size_t sign = (!s.empty() && (s[0] == '+' || s[0] == '-')) ? 1 : 0;
    return s.substr(0, sign) + std::string((size_t)w - s.size(), '0') + s.substr(sign);
}
static inline std::string py_ljust(const std::string& s, long long w, const std::string& f) { return (long long)s.size() >= w ? s : s + std::string((size_t)w - s.size(), f[0]); }
static inline std::string py_rjust(const std::string& s, long long w, const std::string& f) { return (long long)s.size() >= w ? s : std::string((size_t)w - s.size(), f[0]) + s; }
static inline std::string py_center(const std::string& s, long long w, const std::string& f) {
    if ((long long)s.size() >= w) return s;
    long long total = w - (long long)s.size(), left = total / 2 + (total & w & 1);
    return std::string((size_t)left, f[0]) + s + std::string((size_t)(total - left), f[0]);
}
static inline std::string py_removeprefix(const std::string& s, const std::string& p) { return py_startswith(s, p) ? s.substr(p.size()) : s; }
static inline std::string py_removesuffix(const std::string& s, const std::string& p) { return (py_endswith(s, p) && !p.empty()) ? s.substr(0, s.size() - p.size()) : s; }
static inline PyList<std::string> py_chars(const std::string& s) {
    std::vector<std::string> r;
    for (char c : s) r.push_back(std::string(1, c));
    return PyList<std::string>(std::move(r));
}
static inline long long py_ord(const std::string& s) {
    if (s.size() != 1) py_throw("TypeError", "ord() expected a character");
    return (unsigned char)s[0];
}
static inline std::string py_chr(long long n) {
    if (n < 0 || n > 255) py_throw("ValueError", "chr() arg not in range(256) (ASCII/Latin-1 seulement)");
    return std::string(1, (char)n);
}
static inline long long py_int_str(const std::string& s0) {
    std::string s = py_strip(s0, " \t\n\r\v\f", 0);
    size_t i = 0;
    bool neg = false;
    if (i < s.size() && (s[i] == '+' || s[i] == '-')) { neg = s[i] == '-'; i++; }
    if (i >= s.size()) py_throw("ValueError", "invalid literal for int() with base 10: '" + s0 + "'");
    long long v = 0;
    bool prev_digit = false;
    for (; i < s.size(); i++) {
        if (py_digit(s[i])) { v = py_add(py_mul(v, 10), s[i] - '0'); prev_digit = true; }
        else if (s[i] == '_' && prev_digit && i + 1 < s.size() && py_digit(s[i + 1])) prev_digit = false;
        else py_throw("ValueError", "invalid literal for int() with base 10: '" + s0 + "'");
    }
    return neg ? -v : v;
}
template <class T> static inline std::string py_join_star(const PyList<T>& xs, const std::string& sep) {
    std::string r;
    for (size_t i = 0; i < xs.size(); i++) { if (i) r += sep; r += py_str(xs[i]); }
    return r;
}
static inline std::tuple<std::string, std::string, std::string> py_partition(const std::string& s, const std::string& sep) {
    if (sep.empty()) py_throw("ValueError", "empty separator");
    size_t i = s.find(sep);
    if (i == std::string::npos) return std::make_tuple(s, std::string(), std::string());
    return std::make_tuple(s.substr(0, i), sep, s.substr(i + sep.size()));
}
static inline std::tuple<std::string, std::string, std::string> py_rpartition(const std::string& s, const std::string& sep) {
    if (sep.empty()) py_throw("ValueError", "empty separator");
    size_t i = s.rfind(sep);
    if (i == std::string::npos) return std::make_tuple(std::string(), std::string(), s);
    return std::make_tuple(s.substr(0, i), sep, s.substr(i + sep.size()));
}
static inline bool py_isascii(const std::string& s) { for (unsigned char c : s) if (c > 127) return false; return true; }
static inline bool py_isidentifier(const std::string& s) {
    if (s.empty() || (s[0] >= '0' && s[0] <= '9')) return false;
    for (unsigned char c : s) if (!(std::isalnum(c) || c == '_')) return false;
    return true;
}
static inline long long py_srindex(const std::string& s, const std::string& sub) {
    size_t i = s.rfind(sub);
    if (i == std::string::npos) py_throw("ValueError", "substring not found");
    return (long long)i;
}
static inline long long py_int_base(const std::string& s0, long long base) {
    std::string s = py_strip(s0, " \t\n\r\v\f", 0);
    std::string err = "invalid literal for int() with base " + std::to_string(base) + ": '" + s0 + "'";
    if (base < 2 || base > 36) py_throw("ValueError", "int() base must be >= 2 and <= 36");
    size_t i = 0;
    bool neg = false;
    if (i < s.size() && (s[i] == '+' || s[i] == '-')) { neg = s[i] == '-'; i++; }
    if (i + 1 < s.size() && s[i] == '0') {
        char p = (char)std::tolower((unsigned char)s[i + 1]);
        if ((p == 'x' && base == 16) || (p == 'o' && base == 8) || (p == 'b' && base == 2)) i += 2;
    }
    if (i >= s.size()) py_throw("ValueError", err);
    long long v = 0;
    bool prev_digit = false;
    for (; i < s.size(); i++) {
        char c = s[i];
        int d = -1;
        if (c >= '0' && c <= '9') d = c - '0';
        else if (c >= 'a' && c <= 'z') d = c - 'a' + 10;
        else if (c >= 'A' && c <= 'Z') d = c - 'A' + 10;
        if (d >= 0 && d < base) { v = py_add(py_mul(v, base), d); prev_digit = true; }
        else if (c == '_' && prev_digit && i + 1 < s.size()) prev_digit = false;
        else py_throw("ValueError", err);
    }
    return neg ? -v : v;
}
static inline PyList<long long> py_range_list(long long a, long long b, long long s) {
    if (s == 0) py_throw("ValueError", "range() arg 3 must not be zero");
    std::vector<long long> r;
    if (s > 0) for (long long i = a; i < b; i += s) r.push_back(i);
    else for (long long i = a; i > b; i += s) r.push_back(i);
    return PyList<long long>(std::move(r));
}
static inline double py_float_str(const std::string& s0) {
    std::string s = py_strip(s0, " \t\n\r\v\f", 0);
    std::string t;
    for (char c : s) if (c != '_') t += c;
    std::string low = py_lower(t);
    if (low == "inf" || low == "+inf" || low == "infinity" || low == "+infinity") return std::numeric_limits<double>::infinity();
    if (low == "-inf" || low == "-infinity") return -std::numeric_limits<double>::infinity();
    if (low == "nan" || low == "+nan" || low == "-nan") return std::numeric_limits<double>::quiet_NaN();
    if (t.empty()) py_throw("ValueError", "could not convert string to float: '" + s0 + "'");
    for (char c : t) if (!(py_digit(c) || c == '+' || c == '-' || c == '.' || c == 'e' || c == 'E'))
        py_throw("ValueError", "could not convert string to float: '" + s0 + "'");
    char* end = nullptr;
    double v = std::strtod(t.c_str(), &end);
    if (*end != '\0' || end == t.c_str() || py_ws(t[0])) py_throw("ValueError", "could not convert string to float: '" + s0 + "'");
    return v;
}
static inline std::string py_input(const std::string& prompt) {
    std::cout << prompt << std::flush;
    std::string line;
    if (!std::getline(std::cin, line)) py_throw("EOFError", "EOF when reading a line");
    if (!line.empty() && line.back() == '\r') line.pop_back();
    return line;
}

// ---------- tranches (slices) : mêmes règles de normalisation que Python ----------
static inline void py_slice_bounds(long long n, long long lo, bool hasLo, long long hi, bool hasHi, long long step,
                                   long long& start, long long& stop) {
    if (step == 0) py_throw("ValueError", "slice step cannot be zero");
    if (step > 0) {
        start = hasLo ? lo : 0;
        stop = hasHi ? hi : n;
        if (start < 0) { start += n; if (start < 0) start = 0; } else if (start > n) start = n;
        if (stop < 0) { stop += n; if (stop < 0) stop = 0; } else if (stop > n) stop = n;
    } else {
        start = hasLo ? lo : n - 1;
        stop = hasHi ? hi : -n - 1;
        if (start < 0) { start += n; if (start < 0) start = -1; } else if (start >= n) start = n - 1;
        if (stop < 0) { stop += n; if (stop < 0) stop = -1; } else if (stop >= n) stop = n - 1;
    }
}
static inline std::vector<long long> py_slice_indices(long long n, long long lo, bool hasLo, long long hi, bool hasHi, long long step) {
    long long start, stop;
    py_slice_bounds(n, lo, hasLo, hi, hasHi, step, start, stop);
    std::vector<long long> idx;
    if (step > 0) for (long long i = start; i < stop; i += step) idx.push_back(i);
    else for (long long i = start; i > stop; i += step) idx.push_back(i);
    return idx;
}
static inline std::string py_slice(const std::string& s, long long lo, bool hasLo, long long hi, bool hasHi, long long step) {
    std::string r;
    for (long long i : py_slice_indices((long long)s.size(), lo, hasLo, hi, hasHi, step)) r += s[(size_t)i];
    return r;
}
template <class T> static inline PyList<T> py_slice(const PyList<T>& v, long long lo, bool hasLo, long long hi, bool hasHi, long long step) {
    std::vector<T> r;
    for (long long i : py_slice_indices((long long)v.size(), lo, hasLo, hi, hasHi, step)) r.push_back(v[(size_t)i]);
    return PyList<T>(std::move(r));
}
template <class T> static inline void py_setslice(const PyList<T>& v, long long lo, bool hasLo, long long hi, bool hasHi, long long step, const PyList<T>& w) {
    std::vector<T> src(w.begin(), w.end());  // copie : xs[1:3] = xs est valide
    long long n = (long long)v.size();
    if (step == 1) {
        long long start, stop;
        py_slice_bounds(n, lo, hasLo, hi, hasHi, 1, start, stop);
        if (stop < start) stop = start;
        v.erase(v.begin() + start, v.begin() + stop);
        v.insert(v.begin() + start, src.begin(), src.end());
        return;
    }
    auto idx = py_slice_indices(n, lo, hasLo, hi, hasHi, step);
    if (idx.size() != src.size()) py_throw("ValueError", "attempt to assign sequence of size " + std::to_string(src.size()) + " to extended slice of size " + std::to_string(idx.size()));
    for (size_t k = 0; k < idx.size(); k++) v[(size_t)idx[k]] = src[k];
}
template <class T> static inline void py_delslice(const PyList<T>& v, long long lo, bool hasLo, long long hi, bool hasHi, long long step) {
    auto idx = py_slice_indices((long long)v.size(), lo, hasLo, hi, hasHi, step);
    std::sort(idx.begin(), idx.end());
    for (size_t k = idx.size(); k-- > 0;) v.erase(v.begin() + idx[k]);
}
template <class T> static inline void py_delitem(const PyList<T>& v, long long i) {
    long long n = (long long)v.size();
    if (i < 0) i += n;
    if (i < 0 || i >= n) py_throw("IndexError", "list assignment index out of range");
    v.erase(v.begin() + i);
}

// ---------- nombres : arrondi, conversions de base ----------
static inline long long py_f2i(double x) {  // int(float) : tronque vers zéro ; erreur au-delà de 64 bits (limite documentée)
    if (std::isnan(x)) py_throw("ValueError", "cannot convert float NaN to integer");
    if (std::isinf(x) || x >= 9223372036854775808.0 || x < -9223372036854775808.0) py_throw("OverflowError", "entier hors de 64 bits");
    return (long long)x;
}
static inline long long py_round(double x) { return py_f2i(std::nearbyint(x)); }  // arrondi au pair le plus proche, comme Python
static inline double py_round_n(double x, long long n) {
    if (std::isnan(x) || std::isinf(x)) return x;
    if (n > 300) return x;
    char buf[512];
    if (n >= 0) { std::snprintf(buf, sizeof buf, "%.*f", (int)n, x); return std::strtod(buf, nullptr); }
    double p = std::pow(10.0, (double)-n);
    return std::nearbyint(x / p) * p;
}
static inline long long py_powmod(long long a, long long b, long long m) {
    if (m == 0) py_throw("ValueError", "pow() 3rd argument cannot be 0");
    if (b < 0) py_throw("ValueError", "negative exponent with modulus not supported");
    __int128 r = 1, base = ((a % m) + m) % m;
    long long e = b;
    while (e > 0) { if (e & 1) r = r * base % m; base = base * base % m; e >>= 1; }
    long long res = (long long)r;
    if (m < 0 && res != 0) res += m;
    return res;
}
static inline std::string py_based(long long v, int base, const char* prefix, bool upper) {
    if (v == 0) return std::string(prefix) + "0";
    bool neg = v < 0;
    unsigned long long u = neg ? 0ULL - (unsigned long long)v : (unsigned long long)v;
    std::string d;
    while (u) { int r = (int)(u % base); d += (char)(r < 10 ? '0' + r : (upper ? 'A' : 'a') + r - 10); u /= base; }
    std::reverse(d.begin(), d.end());
    return std::string(neg ? "-" : "") + prefix + d;
}
static inline std::string py_bin(long long v) { return py_based(v, 2, "0b", false); }
static inline std::string py_oct(long long v) { return py_based(v, 8, "0o", false); }
static inline std::string py_hex(long long v) { return py_based(v, 16, "0x", false); }
static inline long long py_bit_length(long long v) { unsigned long long u = v < 0 ? 0ULL - (unsigned long long)v : (unsigned long long)v; long long n = 0; while (u) { n++; u >>= 1; } return n; }
static inline long long py_bit_count(long long v) { unsigned long long u = v < 0 ? 0ULL - (unsigned long long)v : (unsigned long long)v; long long n = 0; while (u) { n += (long long)(u & 1); u >>= 1; } return n; }
'''

"""Runtime C++ : format(valeur, spec) selon le mini-langage de format de Python ([[fill]align][sign][#][0][width][,_][.prec][type])."""

FORMAT = r'''
// ---------- format(valeur, spec) : mini-langage de format de Python ----------
struct PySpec {
    char fill = ' ';
    char align = 0;
    char sign = '-';
    bool alt = false, zero = false, fillSet = false;
    long long width = 0, prec = -1;
    char group = 0, type = 0;
};
static inline PySpec py_parse_spec(const std::string& s) {
    PySpec sp;
    size_t i = 0, n = s.size();
    auto is_align = [](char c) { return c == '<' || c == '>' || c == '^' || c == '='; };
    if (n >= 2 && is_align(s[1])) { sp.fill = s[0]; sp.fillSet = true; sp.align = s[1]; i = 2; }
    else if (n >= 1 && is_align(s[0])) { sp.align = s[0]; i = 1; }
    if (i < n && (s[i] == '+' || s[i] == '-' || s[i] == ' ')) sp.sign = s[i++];
    if (i < n && s[i] == '#') { sp.alt = true; i++; }
    if (i < n && s[i] == '0') { sp.zero = true; i++; }
    while (i < n && py_digit(s[i])) sp.width = sp.width * 10 + (s[i++] - '0');
    if (i < n && (s[i] == ',' || s[i] == '_')) sp.group = s[i++];
    if (i < n && s[i] == '.') {
        i++;
        if (i >= n || !py_digit(s[i])) py_throw("ValueError", "Format specifier missing precision");
        sp.prec = 0;
        while (i < n && py_digit(s[i])) sp.prec = sp.prec * 10 + (s[i++] - '0');
    }
    if (i < n) sp.type = s[i++];
    if (i != n) py_throw("ValueError", "Invalid format specifier '" + s + "'");
    return sp;
}
static inline std::string py_pad(const std::string& pre, const std::string& body, const PySpec& sp, char defalign) {
    long long len = (long long)(pre.size() + body.size());
    if (sp.width <= len) return pre + body;
    char align = sp.align ? sp.align : defalign;
    long long pad = sp.width - len;
    char fill = sp.fill;
    if (align == '<') return pre + body + std::string((size_t)pad, fill);
    if (align == '>') return std::string((size_t)pad, fill) + pre + body;
    if (align == '^') { long long left = pad / 2; return std::string((size_t)left, fill) + pre + body + std::string((size_t)(pad - left), fill); }
    return pre + std::string((size_t)pad, fill) + body;  // '=' : le remplissage va entre le signe/préfixe et les chiffres
}
static inline std::string py_group(const std::string& digits, char sep, int every) {
    std::string r;
    int cnt = 0;
    for (size_t i = digits.size(); i-- > 0;) {
        if (cnt == every) { r += sep; cnt = 0; }
        r += digits[i];
        cnt++;
    }
    std::reverse(r.begin(), r.end());
    return r;
}
static inline std::string py_format(const std::string& s, const std::string& spec_s);
static inline std::string py_format(double x, const std::string& spec_s);
// regroupement avec remplissage de zéros : Python insère les séparateurs DANS le remplissage (0,000,123)
static inline std::string py_group_min(const std::string& digits, char sep, int every, long long minw) {
    std::string d = digits;
    while ((long long)py_group(d, sep, every).size() < minw) d = "0" + d;
    return py_group(d, sep, every);
}
// type omis AVEC précision : comme 'g' mais exposant dès decpt > précision-1, et au moins un chiffre après la virgule
static inline std::string py_fmt_none_prec(double a, long long p) {
    if (p == 0) p = 1;
    char b[64];
    std::snprintf(b, sizeof b, "%.*e", (int)(p - 1), a);
    std::string s = b;
    size_t ep = s.find('e');
    int e10 = std::atoi(s.c_str() + ep + 1);
    std::string digs;
    for (size_t i = 0; i < ep; i++) if (s[i] != '.') digs += s[i];
    while (digs.size() > 1 && digs.back() == '0') digs.pop_back();
    int decpt = e10 + 1, n = (int)digs.size();
    if (decpt <= -4 || decpt > p - 1)
        return digs.substr(0, 1) + (n > 1 ? "." + digs.substr(1) : std::string()) + "e" + (e10 < 0 ? "-" : "+") + (std::abs(e10) < 10 ? "0" : "") + std::to_string(std::abs(e10));
    if (decpt <= 0) return "0." + std::string((size_t)-decpt, '0') + digs;
    if (decpt >= n) return digs + std::string((size_t)(decpt - n), '0') + ".0";
    return digs.substr(0, (size_t)decpt) + "." + digs.substr((size_t)decpt);
}
static inline std::string py_format(long long v, const std::string& spec_s) {
    PySpec sp = py_parse_spec(spec_s);
    if (sp.type && std::string("eEfFgG%").find(sp.type) != std::string::npos) return py_format((double)v, spec_s);
    if (sp.type == 'c') return py_format(py_chr(v), std::string(spec_s.begin(), spec_s.end() - 1) + "s");
    if (sp.type != 0 && std::string("dbBoxXn").find(sp.type) == std::string::npos) py_throw("ValueError", std::string("Unknown format code '") + sp.type + "' for object of type 'int'");
    bool neg = v < 0;
    unsigned long long u = neg ? 0ULL - (unsigned long long)v : (unsigned long long)v;
    int base = sp.type == 'b' || sp.type == 'B' ? 2 : sp.type == 'o' ? 8 : (sp.type == 'x' || sp.type == 'X') ? 16 : 10;
    std::string digits;
    if (u == 0) digits = "0";
    while (u) { int r = (int)(u % base); digits += (char)(r < 10 ? '0' + r : (sp.type == 'X' ? 'A' : 'a') + r - 10); u /= base; }
    std::reverse(digits.begin(), digits.end());
    std::string pre = neg ? "-" : (sp.sign == '+' ? "+" : (sp.sign == ' ' ? " " : ""));
    if (sp.alt && base != 10) pre += std::string("0") + (char)(sp.type == 'B' ? 'B' : sp.type);
    if (sp.zero) { if (!sp.fillSet) sp.fill = '0'; if (!sp.align) sp.align = '='; }
    if (sp.group) {
        if (sp.fill == '0' && sp.align == '=') digits = py_group_min(digits, sp.group, base == 10 ? 3 : 4, sp.width - (long long)pre.size());
        else digits = py_group(digits, sp.group, base == 10 ? 3 : 4);
    }
    return py_pad(pre, digits, sp, '>');
}
static inline std::string py_format(double x, const std::string& spec_s) {
    PySpec sp = py_parse_spec(spec_s);
    if (sp.type != 0 && std::string("eEfFgG%").find(sp.type) == std::string::npos) py_throw("ValueError", std::string("Unknown format code '") + sp.type + "' for object of type 'float'");
    bool nan = std::isnan(x), neg = !nan && std::signbit(x);
    double a = std::fabs(x);
    std::string pre = neg ? "-" : (sp.sign == '+' ? "+" : (sp.sign == ' ' ? " " : ""));
    if (sp.zero) { if (!sp.fillSet) sp.fill = '0'; if (!sp.align) sp.align = '='; }
    std::string body;
    if (nan) body = "nan";
    else if (std::isinf(x)) body = "inf";
    else {
        char buf[1024];
        long long prec = sp.prec;
        char t = sp.type;
        if (t == 0 && prec < 0) body = py_str(a);
        else if (t == 0) body = py_fmt_none_prec(a, prec);
        else {
            if (t == '%') { a *= 100.0; t = 'f'; }
            if (prec < 0) prec = 6;
            std::string f = std::string("%") + (sp.alt ? "#" : "") + ".*" + (char)t;
            std::snprintf(buf, sizeof buf, f.c_str(), (int)prec, a);
            body = buf;
            if (sp.type == '%') body += "%";
        }
        if (sp.group) {
            size_t dot = body.find_first_not_of("0123456789");
            std::string ip = body.substr(0, dot == std::string::npos ? body.size() : dot), rest = dot == std::string::npos ? "" : body.substr(dot);
            if (sp.fill == '0' && sp.align == '=') body = py_group_min(ip, sp.group, 3, sp.width - (long long)pre.size() - (long long)rest.size()) + rest;
            else body = py_group(ip, sp.group, 3) + rest;
        }
    }
    if (sp.type == 'F' || sp.type == 'E' || sp.type == 'G') for (auto& c : body) if (c >= 'a' && c <= 'z') c -= 32;
    return py_pad(pre, body, sp, '>');
}
static inline std::string py_format(const std::string& s, const std::string& spec_s) {
    PySpec sp = py_parse_spec(spec_s);
    if (sp.type != 0 && sp.type != 's') py_throw("ValueError", std::string("Unknown format code '") + sp.type + "' for object of type 'str'");
    std::string body = s;
    if (sp.prec >= 0 && (long long)body.size() > sp.prec) body = body.substr(0, (size_t)sp.prec);
    if (sp.zero && !sp.fillSet) sp.fill = '0';
    return py_pad("", body, sp, '<');
}
static inline std::string py_format(bool b, const std::string& spec_s) {
    PySpec sp = py_parse_spec(spec_s);
    if (sp.type != 0 && sp.type != 's') return py_format((long long)b, spec_s);
    return py_format(std::string(b ? "True" : "False"), spec_s);
}
'''

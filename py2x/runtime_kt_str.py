"""Runtime Kotlin : chaînes (ASCII), tranches, arrondi, conversions et format() de Python."""

STRINGS = r'''
// ---------- chaînes : sémantique de Python sur de l'ASCII ----------
fun pyWs(c: Char): Boolean = c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\u000B' || c == '\u000C'
fun pyAlpha(c: Char): Boolean = (c in 'a'..'z') || (c in 'A'..'Z')
fun pyDigit(c: Char): Boolean = c in '0'..'9'
fun pyUpper(s: String): String = buildString { for (c in s) append(if (c in 'a'..'z') c - 32 else c) }
fun pyLower(s: String): String = buildString { for (c in s) append(if (c in 'A'..'Z') c + 32 else c) }
fun pySwapcase(s: String): String = buildString { for (c in s) append(if (c in 'a'..'z') c - 32 else if (c in 'A'..'Z') c + 32 else c) }
fun pyCapitalize(s: String): String { val r = pyLower(s); return if (r.isNotEmpty() && r[0] in 'a'..'z') (r[0] - 32).toString() + r.substring(1) else r }
fun pyTitle(s: String): String {
    val sb = StringBuilder()
    var start = true
    for (c in s) {
        if (pyAlpha(c)) { sb.append(if (start) (if (c in 'a'..'z') c - 32 else c) else (if (c in 'A'..'Z') c + 32 else c)); start = false }
        else { sb.append(c); start = true }
    }
    return sb.toString()
}
fun pyStrip(s: String, chars: String, mode: Long): String {
    var a = 0
    var b = s.length
    if (mode != 2L) while (a < b && chars.indexOf(s[a]) >= 0) a++
    if (mode != 1L) while (b > a && chars.indexOf(s[b - 1]) >= 0) b--
    return s.substring(a, b)
}
fun pySplitWs(s: String): MutableList<String> {
    val r = mutableListOf<String>()
    var i = 0
    val n = s.length
    while (i < n) {
        while (i < n && pyWs(s[i])) i++
        if (i >= n) break
        var j = i
        while (j < n && !pyWs(s[j])) j++
        r.add(s.substring(i, j))
        i = j
    }
    return r
}
fun pySplit(s: String, sep: String, maxsplit: Long): MutableList<String> {
    if (sep.isEmpty()) throw ValueError("empty separator")
    val r = mutableListOf<String>()
    var pos = 0
    var cnt = 0L
    while (maxsplit < 0 || cnt < maxsplit) {
        val f = s.indexOf(sep, pos)
        if (f < 0) break
        r.add(s.substring(pos, f))
        pos = f + sep.length
        cnt++
    }
    r.add(s.substring(pos))
    return r
}
fun pyRsplit(s: String, sep: String, maxsplit: Long): MutableList<String> {
    if (sep.isEmpty()) throw ValueError("empty separator")
    val result = mutableListOf<String>()
    var end = s.length
    var count = 0L
    while (end >= sep.length && (maxsplit < 0 || count < maxsplit)) {
        val found = s.lastIndexOf(sep, end - sep.length)
        if (found < 0) break
        result.add(s.substring(found + sep.length, end))
        end = found
        count++
    }
    result.add(s.substring(0, end))
    result.reverse()
    return result
}
fun pyRsplitWs(s: String, maxsplit: Long): MutableList<String> {
    val result = mutableListOf<String>()
    var end = s.length
    var count = 0L
    while (end > 0 && pyWs(s[end - 1])) end--
    while (end > 0) {
        if (maxsplit >= 0 && count >= maxsplit) {
            result.add(s.substring(0, end))
            break
        }
        var start = end
        while (start > 0 && !pyWs(s[start - 1])) start--
        result.add(s.substring(start, end))
        end = start
        while (end > 0 && pyWs(s[end - 1])) end--
        count++
    }
    result.reverse()
    return result
}
fun pySplitlines(s: String): MutableList<String> {
    val r = mutableListOf<String>()
    var i = 0
    val n = s.length
    while (i < n) {
        var j = i
        while (j < n && s[j] != '\n' && s[j] != '\r') j++
        r.add(s.substring(i, j))
        if (j < n && s[j] == '\r' && j + 1 < n && s[j + 1] == '\n') j++
        i = j + 1
    }
    return r
}
fun pyJoin(sep: String, xs: List<String>): String = xs.joinToString(sep)
fun pyReplace(s: String, from: String, to: String, count: Long): String {
    val sb = StringBuilder()
    var done = 0L
    if (from.isEmpty()) {
        for (i in 0..s.length) {
            if (count < 0 || done < count) { sb.append(to); done++ }
            if (i < s.length) sb.append(s[i])
        }
        return sb.toString()
    }
    var pos = 0
    while (count < 0 || done < count) {
        val f = s.indexOf(from, pos)
        if (f < 0) break
        sb.append(s, pos, f)
        sb.append(to)
        pos = f + from.length
        done++
    }
    sb.append(s, pos, s.length)
    return sb.toString()
}
fun pyStartswith(s: String, p: String): Boolean = s.startsWith(p)
fun pyEndswith(s: String, p: String): Boolean = s.endsWith(p)
fun pyFind(s: String, sub: String): Long = s.indexOf(sub).toLong()
fun pyRfind(s: String, sub: String): Long = s.lastIndexOf(sub).toLong()
fun pySindex(s: String, sub: String): Long {
    val f = s.indexOf(sub)
    if (f < 0) throw ValueError("substring not found")
    return f.toLong()
}
fun pyScount(s: String, sub: String): Long {
    if (sub.isEmpty()) return s.length.toLong() + 1
    var c = 0L
    var pos = 0
    while (true) { val f = s.indexOf(sub, pos); if (f < 0) break; c++; pos = f + sub.length }
    return c
}
fun pyIsdigit(s: String): Boolean = s.isNotEmpty() && s.all { pyDigit(it) }
fun pyIsalpha(s: String): Boolean = s.isNotEmpty() && s.all { pyAlpha(it) }
fun pyIsalnum(s: String): Boolean = s.isNotEmpty() && s.all { pyAlpha(it) || pyDigit(it) }
fun pyIsspace(s: String): Boolean = s.isNotEmpty() && s.all { pyWs(it) }
fun pyIslower(s: String): Boolean = s.any { it in 'a'..'z' } && s.none { it in 'A'..'Z' }
fun pyIsupper(s: String): Boolean = s.any { it in 'A'..'Z' } && s.none { it in 'a'..'z' }
fun pyZfill(s: String, w: Long): String {
    if (s.length >= w) return s
    val sign = if (s.isNotEmpty() && (s[0] == '+' || s[0] == '-')) 1 else 0
    return s.substring(0, sign) + "0".repeat((w - s.length).toInt()) + s.substring(sign)
}
fun pyLjust(s: String, w: Long, f: String): String = if (s.length >= w) s else s + f.repeat((w - s.length).toInt())
fun pyRjust(s: String, w: Long, f: String): String = if (s.length >= w) s else f.repeat((w - s.length).toInt()) + s
fun pyCenter(s: String, w: Long, f: String): String {
    if (s.length >= w) return s
    val total = w - s.length
    val left = total / 2 + (total and w and 1L)
    return f.repeat(left.toInt()) + s + f.repeat((total - left).toInt())
}
fun pyRemoveprefix(s: String, p: String): String = if (s.startsWith(p)) s.substring(p.length) else s
fun pyRemovesuffix(s: String, p: String): String = if (p.isNotEmpty() && s.endsWith(p)) s.substring(0, s.length - p.length) else s
fun pyChars(s: String): MutableList<String> = s.map { it.toString() }.toMutableList()
fun pyOrd(s: String): Long {
    if (s.length != 1) throw TypeError("ord() expected a character")
    return s[0].code.toLong()
}
fun pyChr(n: Long): String {
    if (n < 0 || n > 255) throw ValueError("chr() arg not in range(256) (ASCII/Latin-1 seulement)")
    return n.toInt().toChar().toString()
}
fun pyIntStr(s0: String): Long {
    val s = pyStrip(s0, " \t\n\r\u000B\u000C", 0)
    var i = 0
    var neg = false
    if (i < s.length && (s[i] == '+' || s[i] == '-')) { neg = s[i] == '-'; i++ }
    if (i >= s.length) throw ValueError("invalid literal for int() with base 10: '" + s0 + "'")
    var v = 0L
    var prevDigit = false
    while (i < s.length) {
        if (pyDigit(s[i])) { v = pyAdd(pyMul(v, 10L), (s[i] - '0').toLong()); prevDigit = true }
        else if (s[i] == '_' && prevDigit && i + 1 < s.length && pyDigit(s[i + 1])) prevDigit = false
        else throw ValueError("invalid literal for int() with base 10: '" + s0 + "'")
        i++
    }
    return if (neg) -v else v
}
fun pyPartition(s: String, sep: String): Triple<String, String, String> {
    if (sep.isEmpty()) throw ValueError("empty separator")
    val i = s.indexOf(sep)
    return if (i < 0) Triple(s, "", "") else Triple(s.substring(0, i), sep, s.substring(i + sep.length))
}
fun pyRpartition(s: String, sep: String): Triple<String, String, String> {
    if (sep.isEmpty()) throw ValueError("empty separator")
    val i = s.lastIndexOf(sep)
    return if (i < 0) Triple("", "", s) else Triple(s.substring(0, i), sep, s.substring(i + sep.length))
}
fun pyIsascii(s: String): Boolean = s.all { it.code < 128 }
fun pyIsidentifier(s: String): Boolean = s.isNotEmpty() && !s[0].isDigit() && s.all { it.isLetterOrDigit() || it == '_' }
fun pySrindex(s: String, sub: String): Long { val i = s.lastIndexOf(sub); if (i < 0) throw ValueError("substring not found"); return i.toLong() }
fun pyIntBase(s0: String, base: Long): Long {
    val s = pyStrip(s0, " \t\n\r\u000B\u000C", 0)
    val err = "invalid literal for int() with base " + base + ": '" + s0 + "'"
    if (base < 2 || base > 36) throw ValueError("int() base must be >= 2 and <= 36")
    var i = 0
    var neg = false
    if (i < s.length && (s[i] == '+' || s[i] == '-')) { neg = s[i] == '-'; i++ }
    if (i + 1 < s.length && s[i] == '0') {
        val p = s[i + 1].lowercaseChar()
        if ((p == 'x' && base == 16L) || (p == 'o' && base == 8L) || (p == 'b' && base == 2L)) i += 2
    }
    if (i >= s.length) throw ValueError(err)
    var v = 0L
    var prevDigit = false
    while (i < s.length) {
        val c = s[i]
        val d = if (c in '0'..'9') c - '0' else if (c in 'a'..'z') c - 'a' + 10 else if (c in 'A'..'Z') c - 'A' + 10 else -1
        if (d >= 0 && d < base) { v = pyAdd(pyMul(v, base), d.toLong()); prevDigit = true }
        else if (c == '_' && prevDigit && i + 1 < s.length) prevDigit = false
        else throw ValueError(err)
        i++
    }
    return if (neg) -v else v
}
fun pyRangeList(a: Long, b: Long, s: Long): MutableList<Long> = pyRange(a, b, s).toMutableList()
fun pyFloatStr(s0: String): Double {
    val s = pyStrip(s0, " \t\n\r\u000B\u000C", 0)
    val t = s.replace("_", "")
    val low = pyLower(t)
    if (low == "inf" || low == "+inf" || low == "infinity" || low == "+infinity") return Double.POSITIVE_INFINITY
    if (low == "-inf" || low == "-infinity") return Double.NEGATIVE_INFINITY
    if (low == "nan" || low == "+nan" || low == "-nan") return Double.NaN
    if (t.isEmpty() || t.any { !(pyDigit(it) || it == '+' || it == '-' || it == '.' || it == 'e' || it == 'E') })
        throw ValueError("could not convert string to float: '" + s0 + "'")
    return t.toDoubleOrNull() ?: throw ValueError("could not convert string to float: '" + s0 + "'")
}
fun pyInput(prompt: String): String {
    print(prompt)
    System.out.flush()
    val l = pyStdinReadline()
    if (l.isEmpty()) throw EOFError("EOF when reading a line")
    return l.removeSuffix("\n")
}

fun <K, V> pyDelKey(m: MutableMap<K, V>, k: K) {
    if (!m.containsKey(k)) throw KeyError(k)
    m.remove(k)
}
@Suppress("UNCHECKED_CAST")
fun <K, V> pyDPop(m: MutableMap<K, V>, k: K): V {
    if (!m.containsKey(k)) throw KeyError(k)
    return m.remove(k) as V
}
@Suppress("UNCHECKED_CAST")
fun <K, V> pyDPop(m: MutableMap<K, V>, k: K, d: V): V = if (m.containsKey(k)) m.remove(k) as V else d
@Suppress("UNCHECKED_CAST")
fun <K, V> pySetdefault(m: MutableMap<K, V>, k: K, d: V): V {
    if (!m.containsKey(k)) m[k] = d
    return m[k] as V
}
@Suppress("UNCHECKED_CAST")
fun <K, V> pyDUpdate(m: MutableMap<K, V>, o: Map<K, V>) {
    for ((k, v) in o.toMap()) { if (m is PyFlavDict<K, V> && m.mode == 2) m[k] = (((m[k] as Long?) ?: 0L) + (v as Long)) as V else m[k] = v }
}
fun <K, V> pyDCopy(m: MutableMap<K, V>): MutableMap<K, V> {
    if (m is PyFlavDict<K, V>) { val r = PyFlavDict<K, V>(m.mode, m.fname, m.mk); r.putAll(m); return r }
    return LinkedHashMap(m)
}

inline fun <T, K : Comparable<K>> pySortedKey(xs: List<T>, rev: Boolean, crossinline key: (T) -> K): MutableList<T> =
    (if (rev) xs.sortedByDescending { key(it) } else xs.sortedBy { key(it) }).toMutableList()
inline fun <T, K : Comparable<K>> pySortKey(xs: MutableList<T>, rev: Boolean, crossinline key: (T) -> K) {
    val r = pySortedKey(xs, rev, key)
    xs.clear()
    xs.addAll(r)
}

fun pyRange(a: Long, b: Long, s: Long): LongProgression {
    if (s == 0L) throw ValueError("range() arg 3 must not be zero")
    return if (s > 0) (a until b step s) else (a downTo (b + 1) step -s)
}

// ---------- tranches (slices) ----------
fun pySliceIndices(n: Long, lo: Long?, hi: Long?, step: Long): List<Long> {
    if (step == 0L) throw ValueError("slice step cannot be zero")
    var start: Long
    var stop: Long
    if (step > 0) {
        start = lo ?: 0L
        stop = hi ?: n
        if (start < 0) { start += n; if (start < 0) start = 0 } else if (start > n) start = n
        if (stop < 0) { stop += n; if (stop < 0) stop = 0 } else if (stop > n) stop = n
    } else {
        start = lo ?: (n - 1)
        stop = hi ?: (-n - 1)
        if (start < 0) { start += n; if (start < 0) start = -1 } else if (start >= n) start = n - 1
        if (stop < 0) { stop += n; if (stop < 0) stop = -1 } else if (stop >= n) stop = n - 1
    }
    val idx = mutableListOf<Long>()
    var i = start
    if (step > 0) while (i < stop) { idx.add(i); i += step } else while (i > stop) { idx.add(i); i += step }
    return idx
}
fun pySlice(s: String, lo: Long?, hi: Long?, step: Long): String {
    val sb = StringBuilder()
    for (i in pySliceIndices(s.length.toLong(), lo, hi, step)) sb.append(s[i.toInt()])
    return sb.toString()
}
fun <T> pySlice(v: List<T>, lo: Long?, hi: Long?, step: Long): MutableList<T> {
    val r = mutableListOf<T>()
    for (i in pySliceIndices(v.size.toLong(), lo, hi, step)) r.add(v[i.toInt()])
    return r
}
fun <T> pySetSlice(v: MutableList<T>, lo: Long?, hi: Long?, step: Long, w: List<T>) {
    val src = w.toList()
    val n = v.size.toLong()
    if (step == 1L) {
        val idx = pySliceIndices(n, lo, hi, 1L)
        var start = if (idx.isNotEmpty()) idx.first().toInt() else pySliceStart(n, lo)
        val count = idx.size
        for (k in 0 until count) v.removeAt(start)
        v.addAll(start, src)
        return
    }
    val idx = pySliceIndices(n, lo, hi, step)
    if (idx.size != src.size) throw ValueError("attempt to assign sequence of size " + src.size + " to extended slice of size " + idx.size)
    for (k in idx.indices) v[idx[k].toInt()] = src[k]
}
fun pySliceStart(n: Long, lo: Long?): Int {
    var start = lo ?: 0L
    if (start < 0) { start += n; if (start < 0) start = 0 } else if (start > n) start = n
    return start.toInt()
}
fun <T> pyDelSlice(v: MutableList<T>, lo: Long?, hi: Long?, step: Long) {
    for (i in pySliceIndices(v.size.toLong(), lo, hi, step).sortedDescending()) v.removeAt(i.toInt())
}
fun <T> pyDelItem(v: MutableList<T>, i: Long) {
    val n = v.size
    val j = if (i < 0) i + n else i
    if (j < 0 || j >= n) throw IndexError("list assignment index out of range")
    v.removeAt(j.toInt())
}

// ---------- nombres ----------
fun pyF2i(x: Double): Long {
    if (x.isNaN()) throw ValueError("cannot convert float NaN to integer")
    if (x.isInfinite() || x >= 9.223372036854775808E18 || x < -9.223372036854775808E18) throw OverflowError("entier hors de 64 bits")
    return x.toLong()
}
fun pyRound(x: Double): Long = pyF2i(Math.rint(x))
fun pyRoundN(x: Double, n: Long): Double {
    if (x.isNaN() || x.isInfinite()) return x
    if (n >= 0) return java.math.BigDecimal(x).setScale(n.toInt(), java.math.RoundingMode.HALF_EVEN).toDouble()
    val p = Math.pow(10.0, (-n).toDouble())
    return Math.rint(x / p) * p
}
fun pyPowmod(a: Long, b: Long, m: Long): Long {
    if (m == 0L) throw ValueError("pow() 3rd argument cannot be 0")
    if (b < 0) throw ValueError("negative exponent with modulus not supported")
    var r = java.math.BigInteger.valueOf(a).modPow(java.math.BigInteger.valueOf(b), java.math.BigInteger.valueOf(Math.abs(m))).toLong()
    if (m < 0 && r != 0L) r += m
    return r
}
fun pyBased(v: Long, base: Int, prefix: String): String {
    if (v == 0L) return prefix + "0"
    val s = java.lang.Long.toString(Math.abs(v), base)
    return (if (v < 0) "-" else "") + prefix + s
}
fun pyBin(v: Long): String = pyBased(v, 2, "0b")
fun pyOct(v: Long): String = pyBased(v, 8, "0o")
fun pyHex(v: Long): String = pyBased(v, 16, "0x")
fun pyBitLength(v: Long): Long = (64 - java.lang.Long.numberOfLeadingZeros(Math.abs(v))).toLong()
fun pyBitCount(v: Long): Long = java.lang.Long.bitCount(Math.abs(v)).toLong()
'''

FORMAT = r'''
// ---------- format(valeur, spec) : mini-langage de format de Python ----------
class PySpec(
    var fill: Char = ' ', var align: Char = '\u0000', var sign: Char = '-', var alt: Boolean = false, var zero: Boolean = false,
    var width: Long = 0, var prec: Long = -1, var group: Char = '\u0000', var type: Char = '\u0000', var fillSet: Boolean = false
)
fun pyParseSpec(s: String): PySpec {
    val sp = PySpec()
    var i = 0
    val n = s.length
    fun isAlign(c: Char) = c == '<' || c == '>' || c == '^' || c == '='
    if (n >= 2 && isAlign(s[1])) { sp.fill = s[0]; sp.fillSet = true; sp.align = s[1]; i = 2 }
    else if (n >= 1 && isAlign(s[0])) { sp.align = s[0]; i = 1 }
    if (i < n && (s[i] == '+' || s[i] == '-' || s[i] == ' ')) { sp.sign = s[i]; i++ }
    if (i < n && s[i] == '#') { sp.alt = true; i++ }
    if (i < n && s[i] == '0') { sp.zero = true; i++ }
    while (i < n && pyDigit(s[i])) { sp.width = sp.width * 10 + (s[i] - '0'); i++ }
    if (i < n && (s[i] == ',' || s[i] == '_')) { sp.group = s[i]; i++ }
    if (i < n && s[i] == '.') {
        i++
        if (i >= n || !pyDigit(s[i])) throw ValueError("Format specifier missing precision")
        sp.prec = 0
        while (i < n && pyDigit(s[i])) { sp.prec = sp.prec * 10 + (s[i] - '0'); i++ }
    }
    if (i < n) { sp.type = s[i]; i++ }
    if (i != n) throw ValueError("Invalid format specifier '" + s + "'")
    return sp
}
fun pyPad(pre: String, body: String, sp: PySpec, defalign: Char): String {
    val len = pre.length + body.length
    if (sp.width <= len) return pre + body
    val align = if (sp.align != '\u0000') sp.align else defalign
    val pad = (sp.width - len).toInt()
    val fill = sp.fill.toString()
    return when (align) {
        '<' -> pre + body + fill.repeat(pad)
        '>' -> fill.repeat(pad) + pre + body
        '^' -> { val left = pad / 2; fill.repeat(left) + pre + body + fill.repeat(pad - left) }
        else -> pre + fill.repeat(pad) + body
    }
}
fun pyGroup(digits: String, sep: Char, every: Int): String {
    val sb = StringBuilder()
    var cnt = 0
    for (i in digits.length - 1 downTo 0) {
        if (cnt == every) { sb.append(sep); cnt = 0 }
        sb.append(digits[i])
        cnt++
    }
    return sb.reverse().toString()
}
fun pyFmtFixed(a: Double, prec: Int): String = java.math.BigDecimal(a).setScale(prec, java.math.RoundingMode.HALF_EVEN).toPlainString()
fun pyFmtExp(a: Double, prec: Int, upper: Boolean): String {
    if (a == 0.0) return "0" + (if (prec > 0) "." + "0".repeat(prec) else "") + (if (upper) "E+00" else "e+00")
    val bd = java.math.BigDecimal(a).round(java.math.MathContext(prec + 1, java.math.RoundingMode.HALF_EVEN))
    var digits = bd.unscaledValue().toString()
    val exp = bd.precision() - bd.scale() - 1
    digits = digits.padEnd(prec + 1, '0').substring(0, prec + 1)
    val mant = digits.substring(0, 1) + (if (prec > 0) "." + digits.substring(1) else "")
    return mant + (if (upper) "E" else "e") + (if (exp < 0) "-" else "+") + String.format("%02d", Math.abs(exp))
}
fun pyFmtGeneral(a: Double, prec0: Int, upper: Boolean, alt: Boolean = false): String {
    val prec = if (prec0 == 0) 1 else prec0
    if (a == 0.0) return if (alt) "0." + "0".repeat(prec - 1) else "0"
    val bd = java.math.BigDecimal(a).round(java.math.MathContext(prec, java.math.RoundingMode.HALF_EVEN))
    val x = bd.precision() - bd.scale() - 1
    var s = if (x >= -4 && x < prec) pyFmtFixed(a, Math.max(prec - 1 - x, 0)) else pyFmtExp(a, prec - 1, upper)
    val ePos = s.indexOfFirst { it == 'e' || it == 'E' }
    var mant = if (ePos >= 0) s.substring(0, ePos) else s
    val rest = if (ePos >= 0) s.substring(ePos) else ""
    if (!alt && mant.contains('.')) mant = mant.trimEnd('0').trimEnd('.')
    if (alt && !mant.contains('.')) mant += "."
    return mant + rest
}
fun pyGroupMin(digits: String, sep: Char, every: Int, minw: Long): String {
    var d = digits
    while (pyGroup(d, sep, every).length < minw) d = "0" + d
    return pyGroup(d, sep, every)
}
fun pyFmtNonePrec(a: Double, p0: Long): String {
    val p = if (p0 == 0L) 1 else p0.toInt()
    if (a == 0.0) return "0.0"
    val bd = java.math.BigDecimal(a).round(java.math.MathContext(p, java.math.RoundingMode.HALF_EVEN))
    var digs = bd.unscaledValue().toString().trimEnd('0')
    if (digs.isEmpty()) digs = "0"
    val e10 = bd.precision() - bd.scale() - 1
    val decpt = e10 + 1
    val n = digs.length
    if (decpt <= -4 || decpt > p - 1)
        return digs.substring(0, 1) + (if (n > 1) "." + digs.substring(1) else "") + "e" + (if (e10 < 0) "-" else "+") + String.format("%02d", Math.abs(e10))
    if (decpt <= 0) return "0." + "0".repeat(-decpt) + digs
    if (decpt >= n) return digs + "0".repeat(decpt - n) + ".0"
    return digs.substring(0, decpt) + "." + digs.substring(decpt)
}
fun pyFormat(v: Long, specS: String): String {
    val sp = pyParseSpec(specS)
    if (sp.type != '\u0000' && "eEfFgG%".indexOf(sp.type) >= 0) return pyFormat(v.toDouble(), specS)
    if (sp.type != '\u0000' && "dbBoxXn".indexOf(sp.type) < 0) throw ValueError("Unknown format code '" + sp.type + "' for object of type 'int'")
    val neg = v < 0
    val base = if (sp.type == 'b' || sp.type == 'B') 2 else if (sp.type == 'o') 8 else if (sp.type == 'x' || sp.type == 'X') 16 else 10
    var digits = java.lang.Long.toUnsignedString(if (neg) -v else v, base)
    if (sp.type == 'X') digits = digits.uppercase()
    var pre = if (neg) "-" else if (sp.sign == '+') "+" else if (sp.sign == ' ') " " else ""
    if (sp.alt && base != 10) pre += "0" + (if (sp.type == 'B') 'B' else sp.type)
    if (sp.zero) { if (!sp.fillSet) sp.fill = '0'; if (sp.align == '\u0000') sp.align = '=' }
    if (sp.group != '\u0000') digits = if (sp.fill == '0' && sp.align == '=') pyGroupMin(digits, sp.group, if (base == 10) 3 else 4, sp.width - pre.length) else pyGroup(digits, sp.group, if (base == 10) 3 else 4)
    return pyPad(pre, digits, sp, '>')
}
fun pyFormat(x: Double, specS: String): String {
    val sp = pyParseSpec(specS)
    if (sp.type != '\u0000' && "eEfFgG%".indexOf(sp.type) < 0) throw ValueError("Unknown format code '" + sp.type + "' for object of type 'float'")
    val nan = x.isNaN()
    val neg = !nan && (x < 0 || (x == 0.0 && 1.0 / x < 0))
    var a = Math.abs(x)
    val pre = if (neg) "-" else if (sp.sign == '+') "+" else if (sp.sign == ' ') " " else ""
    if (sp.zero) { if (!sp.fillSet) sp.fill = '0'; if (sp.align == '\u0000') sp.align = '=' }
    var body: String
    if (nan) body = "nan"
    else if (x.isInfinite()) body = "inf"
    else {
        var t = sp.type
        var prec = sp.prec.toInt()
        if (t == '\u0000' && prec < 0) body = pyFloat(a)
        else if (t == '\u0000') body = pyFmtNonePrec(a, sp.prec)
        else {
            if (t == '%') { a *= 100.0; t = 'f' }
            if (prec < 0) prec = 6
            body = when (t) {
                'f', 'F' -> pyFmtFixed(a, prec)
                'e', 'E' -> pyFmtExp(a, prec, t == 'E')
                else -> pyFmtGeneral(a, prec, t == 'G', sp.alt)
            }
            if (sp.alt && prec == 0 && (t == 'f' || t == 'F')) body += "."
            if (sp.alt && prec == 0 && (t == 'e' || t == 'E')) body = body.replaceFirst(Regex("(?=[eE])"), ".")
            if (sp.type == '%') body += "%"
        }
        if (sp.group != '\u0000') {
            val dot = body.indexOfFirst { it !in '0'..'9' }
            val ip = if (dot < 0) body else body.substring(0, dot)
            val rest = if (dot < 0) "" else body.substring(dot)
            body = if (sp.fill == '0' && sp.align == '=') pyGroupMin(ip, sp.group, 3, sp.width - pre.length - rest.length) + rest else pyGroup(ip, sp.group, 3) + rest
        }
    }
    if (sp.type == 'F' || sp.type == 'E' || sp.type == 'G') body = body.uppercase()
    return pyPad(pre, body, sp, '>')
}
fun pyFormat(s: String, specS: String): String {
    val sp = pyParseSpec(specS)
    if (sp.type != '\u0000' && sp.type != 's') throw ValueError("Unknown format code '" + sp.type + "' for object of type 'str'")
    var body = s
    if (sp.prec >= 0 && body.length > sp.prec) body = body.substring(0, sp.prec.toInt())
    if (sp.zero && !sp.fillSet) sp.fill = '0'
    return pyPad("", body, sp, '<')
}
fun pyFormat(b: Boolean, specS: String): String {
    val sp = pyParseSpec(specS)
    if (sp.type != '\u0000' && sp.type != 's') return pyFormat(if (b) 1L else 0L, specS)
    return pyFormat(if (b) "True" else "False", specS)
}
'''

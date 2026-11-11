"""Runtime Kotlin : set (ordre d'itération EXACT de CPython 3.11 pour les entiers), deque, heapq, Counter/defaultdict/OrderedDict."""

COLLECTIONS = r'''
// ---------- set d'entiers : reproduction de la table de hachage de CPython (setobject.c) ----------
class PyIntTab {
    var keys = LongArray(8)
    var hashes = LongArray(8)
    var st = ByteArray(8)  // 0 vide, 1 actif, 2 « dummy » (supprimé)
    var mask = 7
    var fill = 0
    var used = 0
    var finger = 0
    fun hh(k: Long): Long = if (k == -1L) -2L else k
    fun lookup(key: Long, hash: Long): Int {
        var i = (hash and mask.toLong()).toInt()
        var perturb = hash
        while (true) {
            var idx = i
            var probes = if (i + 9 <= mask) 9 else 0
            while (true) {
                if (st[idx].toInt() == 0) return -1
                if (st[idx].toInt() == 1 && hashes[idx] == hash && keys[idx] == key) return idx
                idx++
                if (probes-- == 0) break
            }
            perturb = perturb ushr 5
            i = ((i.toLong() * 5 + 1 + perturb) and mask.toLong()).toInt()
        }
    }
    fun insertClean(nk: LongArray, nh: LongArray, ns: ByteArray, m: Int, key: Long, hash: Long) {
        var i = (hash and m.toLong()).toInt()
        var perturb = hash
        while (true) {
            if (ns[i].toInt() == 0) { nk[i] = key; nh[i] = hash; ns[i] = 1; return }
            if (i + 9 <= m) {
                for (j in 1..9) {
                    if (ns[i + j].toInt() == 0) { nk[i + j] = key; nh[i + j] = hash; ns[i + j] = 1; return }
                }
            }
            perturb = perturb ushr 5
            i = ((i.toLong() * 5 + 1 + perturb) and m.toLong()).toInt()
        }
    }
    fun resize(minused: Int) {
        var newsize = 8
        while (newsize <= minused) newsize = newsize shl 1
        val nk = LongArray(newsize)
        val nh = LongArray(newsize)
        val ns = ByteArray(newsize)
        for (i in 0 until st.size) if (st[i].toInt() == 1) insertClean(nk, nh, ns, newsize - 1, keys[i], hashes[i])
        keys = nk; hashes = nh; st = ns
        mask = newsize - 1
        fill = used
    }
    fun add(key: Long): Boolean {
        val hash = hh(key)
        var i = (hash and mask.toLong()).toInt()
        var perturb = hash
        var freeslot = -1
        var empty = -1
        while (empty < 0) {
            var idx = i
            var probes = if (i + 9 <= mask) 9 else 0
            while (true) {
                val s = st[idx].toInt()
                if (s == 0) { empty = idx; break }
                if (s == 1 && hashes[idx] == hash && keys[idx] == key) return false
                if (s == 2) freeslot = idx
                idx++
                if (probes-- == 0) break
            }
            if (empty >= 0) break
            perturb = perturb ushr 5
            i = ((i.toLong() * 5 + 1 + perturb) and mask.toLong()).toInt()
        }
        if (freeslot >= 0) { used++; keys[freeslot] = key; hashes[freeslot] = hash; st[freeslot] = 1; return true }
        fill++; used++
        keys[empty] = key; hashes[empty] = hash; st[empty] = 1
        if (fill.toLong() * 5 < mask.toLong() * 3) return true
        resize(if (used > 50000) used * 2 else used * 4)
        return true
    }
    fun contains(key: Long): Boolean = lookup(key, hh(key)) >= 0
    fun discard(key: Long): Boolean {
        val idx = lookup(key, hh(key))
        if (idx < 0) return false
        st[idx] = 2; hashes[idx] = -1; used--
        return true
    }
    fun shrinkDummies() { if (fill - used > mask / 4) resize(if (used > 50000) used * 2 else used * 4) }
    fun clear() { keys = LongArray(8); hashes = LongArray(8); st = ByteArray(8); mask = 7; fill = 0; used = 0; finger = 0 }
    fun items(): List<Long> { val r = ArrayList<Long>(); for (i in 0 until st.size) if (st[i].toInt() == 1) r.add(keys[i]); return r }
    fun pop(): Long {
        if (used == 0) throw KeyError("pop from an empty set")
        var i = finger and mask
        while (st[i].toInt() != 1) { i++; if (i > mask) i = 0 }
        val k = keys[i]
        st[i] = 2; hashes[i] = -1; used--
        finger = i + 1
        return k
    }
    fun merge(o: PyIntTab) {
        if (o === this || o.used == 0) return
        if ((fill + o.used).toLong() * 5 >= mask.toLong() * 3) resize((used + o.used) * 2)
        if (fill == 0 && mask == o.mask && o.fill == o.used) {
            for (i in 0..o.mask) if (o.st[i].toInt() == 1) { keys[i] = o.keys[i]; hashes[i] = o.hashes[i]; st[i] = 1 }
            fill = o.fill; used = o.used
            return
        }
        if (fill == 0) {
            fill = o.used; used = o.used
            for (i in 0 until o.st.size) if (o.st[i].toInt() == 1) insertClean(keys, hashes, st, mask, o.keys[i], o.hashes[i])
            return
        }
        for (i in 0 until o.st.size) if (o.st[i].toInt() == 1) add(o.keys[i])
    }
    fun copyFrom(o: PyIntTab) {
        keys = o.keys.copyOf(); hashes = o.hashes.copyOf(); st = o.st.copyOf()
        mask = o.mask; fill = o.fill; used = o.used; finger = o.finger
    }
}

@Suppress("UNCHECKED_CAST")
class PySet<T>(val isInt: Boolean) : Iterable<T> {
    val tab: PyIntTab? = if (isInt) PyIntTab() else null
    val gen: LinkedHashSet<T>? = if (isInt) null else LinkedHashSet()
    val size: Int get() = if (tab != null) tab.used else gen!!.size
    fun items(): MutableList<T> = if (tab != null) tab.items().map { it as T }.toMutableList() else gen!!.toMutableList()
    override fun iterator(): Iterator<T> = items().iterator()
    operator fun contains(x: T): Boolean = if (tab != null) tab.contains(x as Long) else gen!!.contains(x)
    fun add(x: T): Boolean = if (tab != null) tab.add(x as Long) else gen!!.add(x)
    fun discard(x: T): Boolean = if (tab != null) tab.discard(x as Long) else gen!!.remove(x)
    fun clear() { if (tab != null) tab.clear() else gen!!.clear() }
    fun shrinkDummies() { tab?.shrinkDummies() }
    fun pop(): T {
        if (tab != null) return tab.pop() as T
        if (gen!!.isEmpty()) throw KeyError("pop from an empty set")
        val x = gen.first(); gen.remove(x); return x
    }
    fun merge(o: PySet<T>) { if (tab != null) tab.merge(o.tab!!) else gen!!.addAll(o.gen!!) }
    override fun equals(other: Any?): Boolean = other is PySet<*> && size == other.size && items().all { (other as PySet<T>).contains(it) }
    override fun hashCode(): Int = 0
    fun str(): String = if (size == 0) "set()" else items().joinToString(", ", "{", "}") { pyRepr(it) }
}
fun <T> pySetFromList(isInt: Boolean, xs: List<T>): PySet<T> { val r = PySet<T>(isInt); for (x in xs) r.add(x); return r }
fun <T> pySetLit(isInt: Boolean, xs: List<T>, folded: Boolean): PySet<T> {
    val tmp = pySetFromList(isInt, xs)
    if (!folded) return tmp
    val r = PySet<T>(isInt); r.merge(tmp); return r
}
fun <T> pySetCopy(a: PySet<T>): PySet<T> { val r = PySet<T>(a.isInt); r.merge(a); return r }
fun <T> pySetAdd(s: PySet<T>, x: T) { s.add(x) }
fun <T> pySetDiscard(s: PySet<T>, x: T) { s.discard(x) }
fun <T> pySetRemove(s: PySet<T>, x: T) { if (!s.discard(x)) throw KeyError(x) }
fun <T> pySetPop(s: PySet<T>): T = s.pop()
fun <T> pySetClear(s: PySet<T>) { s.clear() }
fun <T> pySetUpdate(s: PySet<T>, xs: List<T>) { for (x in xs) s.add(x) }
fun <T> pySetUpdate(s: PySet<T>, o: PySet<T>) { s.merge(o) }
fun <T> pySetList(s: PySet<T>): MutableList<T> = s.items()
fun <T> pySetUnion(a: PySet<T>, b: PySet<T>): PySet<T> { val r = pySetCopy(a); if (a !== b) r.merge(b); return r }
fun <T> pySetInter(a: PySet<T>, b: PySet<T>): PySet<T> {
    val r = PySet<T>(a.isInt)
    val itSet = if (b.size > a.size) a else b
    val chk = if (b.size > a.size) b else a
    for (x in itSet.items()) if (x in chk) r.add(x)
    return r
}
fun <T> pySetDiff(a: PySet<T>, b: PySet<T>): PySet<T> {
    if ((a.size shr 2) > b.size) { val r = pySetCopy(a); for (x in b.items()) r.discard(x); r.shrinkDummies(); return r }
    val r = PySet<T>(a.isInt)
    for (x in a.items()) if (x !in b) r.add(x)
    return r
}
fun <T> pySetSymdiff(a: PySet<T>, b: PySet<T>): PySet<T> {
    val r = pySetCopy(b)
    for (x in a.items()) if (!r.discard(x)) r.add(x)
    return r
}
fun <T> pySetIssubset(a: PySet<T>, b: PySet<T>): Boolean {
    if (a.size > b.size) return false
    for (x in a.items()) if (x !in b) return false
    return true
}
fun <T> pySetLt(a: PySet<T>, b: PySet<T>): Boolean = a.size < b.size && pySetIssubset(a, b)
fun <T> pySetIsdisjoint(a: PySet<T>, b: PySet<T>): Boolean { for (x in a.items()) if (x in b) return false; return true }
fun <T> pySetIor(a: PySet<T>, b: PySet<T>) { a.merge(b) }
fun <T> pySetIand(a: PySet<T>, b: PySet<T>) {
    val r = pySetInter(a, b)
    if (a.tab != null) { val f = a.tab.finger; a.tab.copyFrom(r.tab!!); a.tab.finger = f } else { a.gen!!.clear(); a.gen.addAll(r.gen!!) }
}
fun <T> pySetIsub(a: PySet<T>, b: PySet<T>) { if (a === b) a.clear() else { for (x in b.items()) a.discard(x); a.shrinkDummies() } }
fun <T> pySetIxor(a: PySet<T>, b: PySet<T>) {
    if (a === b) { a.clear(); return }
    for (x in b.items()) if (!a.discard(x)) a.add(x)
}

// ---------- deque ----------
class PyDeque<T>(val maxlen: Long) : AbstractMutableList<T>() {
    val d = ArrayDeque<T>()
    override val size: Int get() = d.size
    override fun get(index: Int): T = d[index]
    override fun set(index: Int, element: T): T = d.set(index, element)
    override fun add(index: Int, element: T) { d.add(index, element) }
    override fun removeAt(index: Int): T = d.removeAt(index)
    fun str(): String = "deque(" + this.joinToString(", ", "[", "]") { pyRepr(it) } + (if (maxlen >= 0) ", maxlen=$maxlen" else "") + ")"
}
fun <T> pyDqAppend(d: PyDeque<T>, x: T) {
    if (d.maxlen == 0L) return
    if (d.maxlen > 0 && d.size.toLong() == d.maxlen) d.d.removeFirst()
    d.d.addLast(x)
}
fun <T> pyDqAppendleft(d: PyDeque<T>, x: T) {
    if (d.maxlen == 0L) return
    if (d.maxlen > 0 && d.size.toLong() == d.maxlen) d.d.removeLast()
    d.d.addFirst(x)
}
fun <T> pyDqPop(d: PyDeque<T>): T { if (d.d.isEmpty()) throw IndexError("pop from an empty deque"); return d.d.removeLast() }
fun <T> pyDqPopleft(d: PyDeque<T>): T { if (d.d.isEmpty()) throw IndexError("pop from an empty deque"); return d.d.removeFirst() }
fun <T> pyDqExtend(d: PyDeque<T>, xs: List<T>) { for (x in xs.toList()) pyDqAppend(d, x) }
fun <T> pyDqExtendleft(d: PyDeque<T>, xs: List<T>) { for (x in xs.toList()) pyDqAppendleft(d, x) }
fun <T> pyDqClear(d: PyDeque<T>) { d.d.clear() }
fun <T> pyDqRotate(d: PyDeque<T>, n0: Long) {
    val sz = d.size
    if (sz == 0) return
    var n = n0 % sz
    if (n < 0) n += sz
    repeat(n.toInt()) { d.d.addFirst(d.d.removeLast()) }
}
fun <T> pyDqReverse(d: PyDeque<T>) { d.d.reverse() }
fun <T> pyDqList(d: PyDeque<T>): MutableList<T> = d.d.toMutableList()
fun <T> pyDequeFrom(xs: List<T>, maxlen: Long): PyDeque<T> { val d = PyDeque<T>(maxlen); pyDqExtend(d, xs); return d }
fun <T> pyDqCopy(d: PyDeque<T>): PyDeque<T> { val r = PyDeque<T>(d.maxlen); r.d.addAll(d.d); return r }

// ---------- heapq : algorithmes identiques à ceux de CPython ----------
fun <T : Comparable<T>> pySiftdown(h: MutableList<T>, startpos: Int, pos0: Int) {
    var pos = pos0
    val newitem = h[pos]
    while (pos > startpos) {
        val parentpos = (pos - 1) shr 1
        val parent = h[parentpos]
        if (newitem < parent) { h[pos] = parent; pos = parentpos; continue }
        break
    }
    h[pos] = newitem
}
fun <T : Comparable<T>> pySiftup(h: MutableList<T>, pos0: Int) {
    var pos = pos0
    val endpos = h.size
    val startpos = pos
    val newitem = h[pos]
    var childpos = 2 * pos + 1
    while (childpos < endpos) {
        val rightpos = childpos + 1
        if (rightpos < endpos && !(h[childpos] < h[rightpos])) childpos = rightpos
        h[pos] = h[childpos]
        pos = childpos
        childpos = 2 * pos + 1
    }
    h[pos] = newitem
    pySiftdown(h, startpos, pos)
}
fun <T : Comparable<T>> pyHeappush(h: MutableList<T>, x: T) { h.add(x); pySiftdown(h, 0, h.size - 1) }
fun <T : Comparable<T>> pyHeappop(h: MutableList<T>): T {
    if (h.isEmpty()) throw IndexError("index out of range")
    val last = h.removeAt(h.size - 1)
    if (h.isEmpty()) return last
    val ret = h[0]
    h[0] = last
    pySiftup(h, 0)
    return ret
}
fun <T : Comparable<T>> pyHeapreplace(h: MutableList<T>, x: T): T {
    if (h.isEmpty()) throw IndexError("index out of range")
    val ret = h[0]; h[0] = x; pySiftup(h, 0); return ret
}
fun <T : Comparable<T>> pyHeappushpop(h: MutableList<T>, x: T): T {
    if (h.isNotEmpty() && h[0] < x) { val ret = h[0]; h[0] = x; pySiftup(h, 0); return ret }
    return x
}
fun <T : Comparable<T>> pyHeapify(h: MutableList<T>) { var i = h.size / 2; while (i-- > 0) pySiftup(h, i) }
fun <T : Comparable<T>> pyNsmallest(n: Long, xs: List<T>): MutableList<T> = xs.sorted().take(maxOf(n, 0L).toInt()).toMutableList()
fun <T : Comparable<T>> pyNlargest(n: Long, xs: List<T>): MutableList<T> = xs.sortedDescending().take(maxOf(n, 0L).toInt()).toMutableList()

fun <K, V> pyDictPlain(m: MutableMap<K, V>): MutableMap<K, V> = LinkedHashMap(m)
class PyVTuple<T>(val l: MutableList<T>) : AbstractMutableList<T>(), Comparable<PyVTuple<T>> {
    override val size: Int get() = l.size
    override fun get(index: Int): T = l[index]
    override fun set(index: Int, element: T): T = l.set(index, element)
    override fun add(index: Int, element: T) { l.add(index, element) }
    override fun removeAt(index: Int): T = l.removeAt(index)
    override fun compareTo(other: PyVTuple<T>): Int = pyCmpAny(l, other.l)
    fun str(): String = if (size == 1) "(" + pyRepr(l[0]) + ",)" else l.joinToString(", ", "(", ")") { pyRepr(it) }
}
fun <T> pyZipStar(m: List<List<T>>): MutableList<PyVTuple<T>> {
    val r = mutableListOf<PyVTuple<T>>()
    if (m.isEmpty()) return r
    val n = m.minOf { it.size }
    for (j in 0 until n) r.add(PyVTuple(m.map { it[j] }.toMutableList()))
    return r
}
fun <T> pyReduce(xs: List<T>, f: (T, T) -> T): T {
    if (xs.isEmpty()) throw TypeError("reduce() of empty iterable with no initial value")
    var acc = xs[0]
    for (i in 1 until xs.size) acc = f(acc, xs[i])
    return acc
}
fun <T, A> pyReduceInit(xs: List<T>, init: A, f: (A, T) -> A): A {
    var acc = init
    for (x in xs) acc = f(acc, x)
    return acc
}

// ---------- générateurs : Iterator<T> construit par iterator { yield(...) } ----------
fun <T> pyGenNext(g: Iterator<T>): T { if (!g.hasNext()) throw StopIteration(""); return g.next() }
fun <T> pyGenNextDefault(g: Iterator<T>, d: T): T = if (g.hasNext()) g.next() else d
fun <T> pyGenTake(g: Iterator<T>, n: Long): MutableList<T> {
    val r = mutableListOf<T>()
    while (r.size.toLong() < n && g.hasNext()) r.add(g.next())
    return r
}

// ---------- bisect ----------
fun <T : Comparable<T>> pyBisectLeft(xs: List<T>, x: T): Long {
    var lo = 0; var hi = xs.size
    while (lo < hi) { val mid = (lo + hi) / 2; if (xs[mid] < x) lo = mid + 1 else hi = mid }
    return lo.toLong()
}
fun <T : Comparable<T>> pyBisectRight(xs: List<T>, x: T): Long {
    var lo = 0; var hi = xs.size
    while (lo < hi) { val mid = (lo + hi) / 2; if (x < xs[mid]) hi = mid else lo = mid + 1 }
    return lo.toLong()
}
fun <T : Comparable<T>> pyInsortLeft(xs: MutableList<T>, x: T) { xs.add(pyBisectLeft(xs, x).toInt(), x) }
fun <T : Comparable<T>> pyInsortRight(xs: MutableList<T>, x: T) { xs.add(pyBisectRight(xs, x).toInt(), x) }

// ---------- itertools ----------
fun <T> pyProductRep(xs: List<T>, k: Long): MutableList<PyVTuple<T>> {
    val out = mutableListOf<PyVTuple<T>>()
    val cur = mutableListOf<T>()
    fun rec() {
        if (cur.size.toLong() == k) { out.add(PyVTuple(cur.toMutableList())); return }
        for (x in xs) { cur.add(x); rec(); cur.removeAt(cur.size - 1) }
    }
    rec()
    return out
}
fun <T> pyPermutationsVec(xs: List<T>, r0: Long): MutableList<PyVTuple<T>> {
    val n = xs.size
    val r = if (r0 < 0) n.toLong() else r0
    val out = mutableListOf<PyVTuple<T>>()
    if (r > n) return out
    val used = BooleanArray(n)
    val cur = mutableListOf<T>()
    fun rec() {
        if (cur.size.toLong() == r) { out.add(PyVTuple(cur.toMutableList())); return }
        for (i in 0 until n) if (!used[i]) { used[i] = true; cur.add(xs[i]); rec(); cur.removeAt(cur.size - 1); used[i] = false }
    }
    rec()
    return out
}
fun <T> pyCombinationsVec(xs: List<T>, r: Long): MutableList<PyVTuple<T>> {
    val n = xs.size
    val out = mutableListOf<PyVTuple<T>>()
    if (r < 0 || r > n) return out
    val cur = mutableListOf<T>()
    fun rec(start: Int) {
        if (cur.size.toLong() == r) { out.add(PyVTuple(cur.toMutableList())); return }
        for (i in start until n) { cur.add(xs[i]); rec(i + 1); cur.removeAt(cur.size - 1) }
    }
    rec(0)
    return out
}
fun <T> pyCombinationsWithReplacementVec(xs: List<T>, r: Long): MutableList<PyVTuple<T>> {
    val n = xs.size
    val out = mutableListOf<PyVTuple<T>>()
    if (r < 0 || (n == 0 && r > 0)) return out
    val cur = mutableListOf<T>()
    fun rec(start: Int) {
        if (cur.size.toLong() == r) { out.add(PyVTuple(cur.toMutableList())); return }
        for (i in start until n) { cur.add(xs[i]); rec(i); cur.removeAt(cur.size - 1) }
    }
    rec(0)
    return out
}
fun <T> pyAccumulate(xs: List<T>, f: (T, T) -> T): MutableList<T> {
    val r = mutableListOf<T>()
    for ((i, x) in xs.withIndex()) r.add(if (i == 0) x else f(r[r.size - 1], x))
    return r
}
fun <T> pyAccumulateInit(xs: List<T>, init: T, f: (T, T) -> T): MutableList<T> {
    val r = mutableListOf(init)
    for (x in xs) r.add(f(r[r.size - 1], x))
    return r
}
fun <T> pyFlatten(xs: List<List<T>>): MutableList<T> { val r = mutableListOf<T>(); for (l in xs) r.addAll(l); return r }
fun <K, V> pyDictMerge(a: MutableMap<K, V>, b: MutableMap<K, V>): MutableMap<K, V> { val r = LinkedHashMap<K, V>(); r.putAll(a); r.putAll(b); return r }

// ---------- entrées / sorties standard ----------
val pyStdin = System.`in`.bufferedReader(Charsets.UTF_8)
fun pyStdinRead(): String = pyStdin.readText().replace("\r\n", "\n")
fun pyStdinReadline(): String {
    val sb = StringBuilder()
    while (true) {
        val c = pyStdin.read()
        if (c < 0) break
        if (c == '\r'.code) {
            pyStdin.mark(1)
            val d = pyStdin.read()
            if (d == '\n'.code) { sb.append('\n'); break }
            pyStdin.reset()
        }
        sb.append(c.toChar())
        if (c == '\n'.code) break
    }
    return sb.toString()
}
fun pyStdinReadlines(): MutableList<String> {
    val r = mutableListOf<String>()
    while (true) { val l = pyStdinReadline(); if (l.isEmpty()) break; r.add(l) }
    return r
}
fun pyStdoutWrite(s: String) { print(s) }
fun pyStderrWrite(s: String) { System.err.print(s) }
fun pyStdoutFlush() { System.out.flush() }

// ---------- math : domaines et dépassements comme en Python ----------
fun pySqrt(x: Double): Double { if (x < 0) throw ValueError("math domain error"); return Math.sqrt(x) }
fun pyLog(x: Double): Double { if (x <= 0) throw ValueError("math domain error"); return Math.log(x) }
fun pyLog2(x: Double): Double { if (x <= 0) throw ValueError("math domain error"); return Math.log(x) / Math.log(2.0) }
fun pyLog10(x: Double): Double { if (x <= 0) throw ValueError("math domain error"); return Math.log10(x) }
fun pyLog1p(x: Double): Double { if (x <= -1) throw ValueError("math domain error"); return Math.log1p(x) }
fun pyAsin(x: Double): Double { if (x < -1 || x > 1) throw ValueError("math domain error"); return Math.asin(x) }
fun pyAcos(x: Double): Double { if (x < -1 || x > 1) throw ValueError("math domain error"); return Math.acos(x) }
fun pyExp(x: Double): Double { val r = Math.exp(x); if (r.isInfinite() && !x.isInfinite()) throw OverflowError("math range error"); return r }
fun pyExpm1(x: Double): Double { val r = Math.expm1(x); if (r.isInfinite() && !x.isInfinite()) throw OverflowError("math range error"); return r }
fun pyFpow(a: Double, b: Double): Double {
    if (a == 0.0 && b < 0) throw ZeroDivisionError("0.0 cannot be raised to a negative power")
    if (a < 0 && b != Math.floor(b) && !b.isInfinite()) throw ValueError("negative number raised to a fractional power gives a complex result (not supported)")
    val r = Math.pow(a, b)
    if (r.isInfinite() && !a.isInfinite() && !b.isInfinite()) throw OverflowError("(34, 'Result too large')")
    return r
}
fun pyMpow(a: Double, b: Double): Double {
    if (a == 0.0 && b < 0) throw ValueError("math domain error")
    if (a < 0 && b != Math.floor(b) && !b.isInfinite()) throw ValueError("math domain error")
    val r = Math.pow(a, b)
    if (r.isInfinite() && !a.isInfinite() && !b.isInfinite()) throw OverflowError("math range error")
    return r
}
fun pyIsclose(a: Double, b: Double): Boolean {
    if (a == b) return true
    if (a.isInfinite() || b.isInfinite()) return false
    return Math.abs(a - b) <= maxOf(1e-9 * maxOf(Math.abs(a), Math.abs(b)), 0.0)
}
fun pyComb(n: Long, k0: Long): Long {
    if (n < 0 || k0 < 0) throw ValueError("n and k must be non-negative integers")
    if (k0 > n) return 0L
    val k = if (k0 > n - k0) n - k0 else k0
    var r = 1L
    for (i in 1..k) r = pyMul(r, n - k + i) / i
    return r
}
fun pyPerm(n: Long, k: Long): Long {
    if (n < 0 || k < 0) throw ValueError("n and k must be non-negative integers")
    if (k > n) return 0L
    var r = 1L
    for (i in 0 until k) r = pyMul(r, n - i)
    return r
}
fun pyProdI(x: List<Long>): Long { var p = 1L; for (v in x) p = pyMul(p, v); return p }
// ---------- Counter / defaultdict / OrderedDict : dict avec comportement propre ----------
class PyFlavDict<K, V>(val mode: Int, val fname: String, val mk: () -> V) : LinkedHashMap<K, V>()
fun <K, V> pyDGet(d: MutableMap<K, V>, k: K): V {
    if (d is PyFlavDict<K, V> && !d.containsKey(k)) {
        if (d.mode == 1) { val v = d.mk(); d[k] = v; return v }
        if (d.mode == 2) return d.mk()
    }
    if (!d.containsKey(k)) throw KeyError(k)
    @Suppress("UNCHECKED_CAST") return d[k] as V
}
fun pyFlavStr(d: PyFlavDict<*, *>): String {
    val body = d.entries.joinToString(", ", "{", "}") { pyRepr(it.key) + ": " + pyRepr(it.value) }
    return when (d.mode) {
        1 -> "defaultdict(" + d.fname + ", " + body + ")"
        2 -> if (d.isEmpty()) "Counter()" else "Counter(" + d.entries.sortedByDescending { it.value as Long }.joinToString(", ", "{", "}") { pyRepr(it.key) + ": " + pyRepr(it.value) } + ")"
        3 -> if (d.isEmpty()) "OrderedDict()" else d.entries.joinToString(", ", "OrderedDict([", "])") { "(" + pyRepr(it.key) + ", " + pyRepr(it.value) + ")" }
        else -> body
    }
}
fun <K> pyCounterFrom(xs: List<K>): MutableMap<K, Long> {
    val d = PyFlavDict<K, Long>(2, "") { 0L }
    for (x in xs) d[x] = (d[x] ?: 0L) + 1L
    return d
}
fun <K> pyCounterUpdate(d: MutableMap<K, Long>, xs: List<K>) { for (x in xs.toList()) d[x] = (d[x] ?: 0L) + 1L }
fun <K> pyMostCommon(d: MutableMap<K, Long>, n: Long): List<Pair<K, Long>> {
    val r = d.entries.map { Pair(it.key, it.value) }.sortedByDescending { it.second }
    return if (n >= 0 && n < r.size) r.take(n.toInt()) else r
}
fun <K> pyCounterTotal(d: MutableMap<K, Long>): Long = d.values.sum()
fun <K> pyCounterElements(d: MutableMap<K, Long>): MutableList<K> {
    val r = mutableListOf<K>()
    for ((k, v) in d) { var i = 0L; while (i < v) { r.add(k); i++ } }
    return r
}
fun <K, V> pyMoveToEnd(d: MutableMap<K, V>, k: K, last: Boolean) {
    if (!d.containsKey(k)) throw KeyError(k)
    if (last) { val v = d.remove(k) as V; d[k] = v; return }
    val v = d.remove(k) as V
    val rest = d.entries.map { Pair(it.key, it.value) }
    d.clear()
    d[k] = v
    for ((a, b) in rest) d[a] = b
}
fun <K, V> pyPopitemAt(d: MutableMap<K, V>, last: Boolean): Pair<K, V> {
    if (d.isEmpty()) throw KeyError("dictionary is empty")
    val e = if (last) d.entries.last() else d.entries.first()
    val r = Pair(e.key, e.value)
    d.remove(r.first)
    return r
}
'''

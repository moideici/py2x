"""Runtime C++ : set (ordre d'itération EXACT de CPython 3.11 pour les entiers), deque, heapq, Counter."""

COLLECTIONS = r'''
// ---------- set d'entiers : reproduction exacte de la table de hachage de CPython 3.11 (setobject.c) ----------
struct PyIntSetImpl {
    struct E { long long key = 0; long long hash = 0; unsigned char st = 0; };  // st : 0 vide, 1 actif, 2 « dummy » (supprimé)
    std::vector<E> t;
    size_t mask = 7, fill = 0, used = 0, finger = 0;
    static constexpr int LP = 9;  // LINEAR_PROBES
    PyIntSetImpl() : t(8) {}
    static long long hh(long long k) { return k == -1 ? -2 : k; }  // hash(int) de Python
    long long lookup(long long key, long long hash) const {
        size_t i = (size_t)hash & mask;
        unsigned long long perturb = (unsigned long long)hash;
        while (true) {
            size_t idx = i;
            int probes = (i + LP <= mask) ? LP : 0;
            do {
                const E& e = t[idx];
                if (e.st == 0) return -1;
                if (e.st == 1 && e.hash == hash && e.key == key) return (long long)idx;
                idx++;
            } while (probes--);
            perturb >>= 5;
            i = (i * 5 + 1 + (size_t)perturb) & mask;
        }
    }
    static void insert_clean(std::vector<E>& tab, size_t m, long long key, long long hash) {
        size_t i = (size_t)hash & m;
        unsigned long long perturb = (unsigned long long)hash;
        while (true) {
            if (tab[i].st == 0) { tab[i].key = key; tab[i].hash = hash; tab[i].st = 1; return; }
            if (i + LP <= m) {
                for (int j = 1; j <= LP; j++) {
                    if (tab[i + j].st == 0) { tab[i + j].key = key; tab[i + j].hash = hash; tab[i + j].st = 1; return; }
                }
            }
            perturb >>= 5;
            i = (i * 5 + 1 + (size_t)perturb) & m;
        }
    }
    void resize(size_t minused) {
        size_t newsize = 8;
        while (newsize <= minused) newsize <<= 1;
        std::vector<E> nt(newsize);
        for (const E& e : t) if (e.st == 1) insert_clean(nt, newsize - 1, e.key, e.hash);
        t = std::move(nt);
        mask = newsize - 1;
        fill = used;
    }
    bool add(long long key) {
        long long hash = hh(key);
        size_t i = (size_t)hash & mask;
        unsigned long long perturb = (unsigned long long)hash;
        long long freeslot = -1, empty = -1;
        while (empty < 0) {
            size_t idx = i;
            int probes = (i + LP <= mask) ? LP : 0;
            do {
                const E& e = t[idx];
                if (e.st == 0) { empty = (long long)idx; break; }
                if (e.st == 1 && e.hash == hash && e.key == key) return false;
                if (e.st == 2) freeslot = (long long)idx;  // CPython 3.11 : c'est la DERNIÈRE case « dummy » rencontrée qui est réutilisée
                idx++;
            } while (probes--);
            if (empty >= 0) break;
            perturb >>= 5;
            i = (i * 5 + 1 + (size_t)perturb) & mask;
        }
        if (freeslot >= 0) { used++; E& e = t[(size_t)freeslot]; e.key = key; e.hash = hash; e.st = 1; return true; }
        fill++; used++;
        E& e = t[(size_t)empty]; e.key = key; e.hash = hash; e.st = 1;
        if (fill * 5 < mask * 3) return true;
        resize(used > 50000 ? used * 2 : used * 4);
        return true;
    }
    bool contains(long long key) const { return lookup(key, hh(key)) >= 0; }
    bool discard(long long key) {
        long long idx = lookup(key, hh(key));
        if (idx < 0) return false;
        E& e = t[(size_t)idx]; e.st = 2; e.hash = -1; used--;
        return true;
    }
    size_t finger_get() const { return finger; }
    void finger_set(size_t f) { finger = f; }
    size_t size() const { return used; }
    void shrink_dummies() { if (fill - used > mask / 4) resize(used > 50000 ? used * 2 : used * 4); }  // fin de set_difference_update_internal
    void clear() { t.assign(8, E()); mask = 7; fill = used = finger = 0; }
    std::vector<long long> items() const { std::vector<long long> r; for (const E& e : t) if (e.st == 1) r.push_back(e.key); return r; }
    long long pop() {
        if (used == 0) py_throw("KeyError", "'pop from an empty set'");
        size_t i = finger & mask;
        while (t[i].st != 1) { i++; if (i > mask) i = 0; }
        long long k = t[i].key;
        t[i].st = 2; t[i].hash = -1; used--;
        finger = i + 1;
        return k;
    }
    void merge(const PyIntSetImpl& o) {  // set_merge
        if (&o == this || o.used == 0) return;
        if ((fill + o.used) * 5 >= mask * 3) resize((used + o.used) * 2);
        if (fill == 0 && mask == o.mask && o.fill == o.used) {
            for (size_t i = 0; i <= o.mask; i++) if (o.t[i].st == 1) t[i] = o.t[i];
            fill = o.fill; used = o.used;
            return;
        }
        if (fill == 0) {
            fill = used = o.used;
            for (const E& e : o.t) if (e.st == 1) insert_clean(t, mask, e.key, e.hash);
            return;
        }
        for (const E& e : o.t) if (e.st == 1) add(e.key);
    }
};

// ---------- set générique (str, tuples...) : ordre d'insertion. L'ordre de Python y est aléatoire d'une exécution à l'autre ----------
template <class T> struct PyGenSetImpl {
    std::vector<T> e;
    std::map<T, size_t> idx;
    bool add(const T& x) { if (idx.count(x)) return false; idx[x] = e.size(); e.push_back(x); return true; }
    bool contains(const T& x) const { return idx.count(x) > 0; }
    bool discard(const T& x) {
        auto it = idx.find(x);
        if (it == idx.end()) return false;
        size_t i = it->second;
        idx.erase(it);
        e.erase(e.begin() + i);
        for (size_t j = i; j < e.size(); j++) idx[e[j]] = j;
        return true;
    }
    size_t finger_get() const { return 0; }
    void finger_set(size_t) {}
    size_t size() const { return e.size(); }
    void shrink_dummies() {}
    void clear() { e.clear(); idx.clear(); }
    std::vector<T> items() const { return e; }
    T pop() { if (e.empty()) py_throw("KeyError", "'pop from an empty set'"); T x = e.front(); discard(x); return x; }
    void merge(const PyGenSetImpl& o) { for (const auto& x : o.e) add(x); }
};
template <class T, bool IsInt = std::is_same<T, long long>::value || std::is_same<T, bool>::value> struct PySetSel { using type = PyGenSetImpl<T>; };
template <class T> struct PySetSel<T, true> { using type = PyIntSetImpl; };

template <class T> struct PySet {
    using value_type = T;
    using Impl = typename PySetSel<T>::type;
    std::shared_ptr<Impl> p;
    PySet() : p(std::make_shared<Impl>()) {}
    size_t size() const { return p->size(); }
    bool contains(const T& x) const { return p->contains(x); }
    bool add(const T& x) const { return p->add(x); }
    bool discard(const T& x) const { return p->discard(x); }
    void clear() const { p->clear(); }
    void shrink_dummies() const { p->shrink_dummies(); }
    std::vector<T> items() const { std::vector<T> r; for (auto k : p->items()) r.push_back((T)k); return r; }
    T pop() const { return (T)p->pop(); }
    void merge(const PySet& o) const { p->merge(*o.p); }
};
template <class T> static inline PySet<T> py_set_copy(const PySet<T>& a) { PySet<T> r; r.merge(a); return r; }
template <class T> static inline PySet<T> py_set_lit(const PyList<T>& xs) { PySet<T> r; for (const auto& x : xs) r.add(x); return r; }
// littéral de 3 constantes ou plus : CPython construit un frozenset constant puis le FUSIONNE dans le set (SET_UPDATE)
template <class T> static inline PySet<T> py_set_lit_folded(const PyList<T>& xs) { PySet<T> tmp = py_set_lit(xs), r; r.merge(tmp); return r; }
template <class T> static inline PySet<T> py_set_from(const PyList<T>& xs) { PySet<T> r; for (const auto& x : xs) r.add(x); return r; }
template <class T> static inline PySet<T> py_set_from(const PySet<T>& s) { return py_set_copy(s); }
template <class T> static inline void py_set_add(const PySet<T>& s, const T& x) { s.add(x); }
template <class T> static inline void py_set_discard(const PySet<T>& s, const T& x) { s.discard(x); }
template <class T> static inline void py_set_remove(const PySet<T>& s, const T& x) { if (!s.discard(x)) py_throw("KeyError", py_repr_any(x)); }
template <class T> static inline T py_set_pop(const PySet<T>& s) { return s.pop(); }
template <class T> static inline void py_set_clear(const PySet<T>& s) { s.clear(); }
template <class T> static inline void py_set_update(const PySet<T>& s, const PyList<T>& xs) { for (const auto& x : xs) s.add(x); }
template <class T> static inline void py_set_update(const PySet<T>& s, const PySet<T>& o) { s.merge(o); }
template <class T> static inline void py_set_ior(const PySet<T>& a, const PySet<T>& b) { a.merge(b); }
template <class T> static inline void py_set_iand(const PySet<T>& a, const PySet<T>& b);
template <class T> static inline void py_set_isub(const PySet<T>& a, const PySet<T>& b) { if (a.p == b.p) a.clear(); else { for (const auto& x : b.items()) a.discard(x); a.shrink_dummies(); } }
template <class T> static inline void py_set_ixor(const PySet<T>& a, const PySet<T>& b) {
    if (a.p == b.p) { a.clear(); return; }
    for (const auto& x : b.items()) if (!a.discard(x)) a.add(x);
}
template <class T> static inline PyList<T> py_set_list(const PySet<T>& s) { return PyList<T>(s.items()); }
template <class T> static inline PySet<T> py_set_union(const PySet<T>& a, const PySet<T>& b) { PySet<T> r = py_set_copy(a); if (a.p != b.p) r.merge(b); return r; }
template <class T> static inline PySet<T> py_set_inter(const PySet<T>& a, const PySet<T>& b) {
    PySet<T> r;
    const PySet<T>& it = b.size() > a.size() ? a : b;   // on parcourt le plus petit (CPython : set_intersection)
    const PySet<T>& chk = b.size() > a.size() ? b : a;
    for (const auto& x : it.items()) if (chk.contains(x)) r.add(x);
    return r;
}
template <class T> static inline void py_set_iand(const PySet<T>& a, const PySet<T>& b) { PySet<T> r = py_set_inter(a, b); auto f = a.p->finger_get(); *a.p = *r.p; a.p->finger_set(f); }
template <class T> static inline PySet<T> py_set_diff(const PySet<T>& a, const PySet<T>& b) {
    if ((a.size() >> 2) > b.size()) { PySet<T> r = py_set_copy(a); for (const auto& x : b.items()) r.discard(x); r.shrink_dummies(); return r; }
    PySet<T> r;
    for (const auto& x : a.items()) if (!b.contains(x)) r.add(x);
    return r;
}
template <class T> static inline PySet<T> py_set_symdiff(const PySet<T>& a, const PySet<T>& b) {
    PySet<T> r = py_set_copy(b);
    for (const auto& x : a.items()) if (!r.discard(x)) r.add(x);
    return r;
}
template <class T> static inline bool py_set_issubset(const PySet<T>& a, const PySet<T>& b) {
    if (a.size() > b.size()) return false;
    for (const auto& x : a.items()) if (!b.contains(x)) return false;
    return true;
}
template <class T> static inline bool py_set_eq(const PySet<T>& a, const PySet<T>& b) { return a.size() == b.size() && py_set_issubset(a, b); }
template <class T> static inline bool py_set_lt(const PySet<T>& a, const PySet<T>& b) { return a.size() < b.size() && py_set_issubset(a, b); }
template <class T> static inline bool py_set_isdisjoint(const PySet<T>& a, const PySet<T>& b) { for (const auto& x : a.items()) if (b.contains(x)) return false; return true; }
template <class T> bool py_eq(const PySet<T>& a, const PySet<T>& b) { return py_set_eq(a, b); }
template <class T> std::string py_str(const PySet<T>& s) {
    if (s.size() == 0) return "set()";
    std::string r = "{";
    bool first = true;
    for (const auto& x : s.items()) { if (!first) r += ", "; first = false; r += py_repr(x); }
    return r + "}";
}
template <class T, class X> static inline bool py_in(const PySet<T>& s, const X& x) { return s.contains((T)x); }

// ---------- deque ----------
template <class T> struct PyDeque {
    using value_type = T;
    std::shared_ptr<std::deque<T>> p;
    long long maxlen;
    PyDeque(long long ml = -1) : p(std::make_shared<std::deque<T>>()), maxlen(ml) {}
    size_t size() const { return p->size(); }
    bool empty() const { return p->empty(); }
    T& operator[](size_t i) const { return (*p)[i]; }
    auto begin() const { return p->begin(); }
    auto end() const { return p->end(); }
};
template <class T> static inline void py_dq_append(const PyDeque<T>& d, const T& x) {
    if (d.maxlen == 0) return;
    if (d.maxlen > 0 && (long long)d.p->size() == d.maxlen) d.p->pop_front();
    d.p->push_back(x);
}
template <class T> static inline void py_dq_appendleft(const PyDeque<T>& d, const T& x) {
    if (d.maxlen == 0) return;
    if (d.maxlen > 0 && (long long)d.p->size() == d.maxlen) d.p->pop_back();
    d.p->push_front(x);
}
template <class T> static inline T py_dq_pop(const PyDeque<T>& d) {
    if (d.p->empty()) py_throw("IndexError", "pop from an empty deque");
    T x = d.p->back(); d.p->pop_back(); return x;
}
template <class T> static inline T py_dq_popleft(const PyDeque<T>& d) {
    if (d.p->empty()) py_throw("IndexError", "pop from an empty deque");
    T x = d.p->front(); d.p->pop_front(); return x;
}
template <class T> static inline void py_dq_extend(const PyDeque<T>& d, const PyList<T>& xs) { std::vector<T> t(xs.begin(), xs.end()); for (const auto& x : t) py_dq_append(d, x); }
template <class T> static inline void py_dq_extendleft(const PyDeque<T>& d, const PyList<T>& xs) { std::vector<T> t(xs.begin(), xs.end()); for (const auto& x : t) py_dq_appendleft(d, x); }
template <class T> static inline void py_dq_clear(const PyDeque<T>& d) { d.p->clear(); }
template <class T> static inline void py_dq_rotate(const PyDeque<T>& d, long long n) {
    long long sz = (long long)d.p->size();
    if (sz == 0) return;
    n %= sz; if (n < 0) n += sz;
    std::rotate(d.p->begin(), d.p->begin() + (sz - n), d.p->end());
}
template <class T> static inline void py_dq_reverse(const PyDeque<T>& d) { std::reverse(d.p->begin(), d.p->end()); }
template <class T> static inline PyList<T> py_dq_list(const PyDeque<T>& d) { return PyList<T>(std::vector<T>(d.p->begin(), d.p->end())); }
template <class T> static inline PyDeque<T> py_deque_from(const PyList<T>& xs, long long maxlen) { PyDeque<T> d(maxlen); py_dq_extend(d, xs); return d; }
template <class T> static inline PyDeque<T> py_dq_copy(const PyDeque<T>& d) { PyDeque<T> r(d.maxlen); *r.p = *d.p; return r; }
template <class T> bool py_eq(const PyDeque<T>& a, const PyDeque<T>& b) {
    if (a.size() != b.size()) return false;
    for (size_t i = 0; i < a.size(); i++) if (!py_eq(a[i], b[i])) return false;
    return true;
}
template <class T> std::string py_str(const PyDeque<T>& d) {
    std::string r = "deque([";
    for (size_t i = 0; i < d.size(); i++) { if (i) r += ", "; r += py_repr(d[i]); }
    r += "]";
    if (d.maxlen >= 0) r += ", maxlen=" + std::to_string(d.maxlen);
    return r + ")";
}
template <class T, class X> static inline bool py_in(const PyDeque<T>& d, const X& x) { for (const auto& e : d) if (py_eq(e, x)) return true; return false; }

// ---------- heapq : algorithmes identiques à ceux de CPython (même disposition du tas) ----------
template <class T> static inline void py_siftdown(const PyList<T>& h, size_t startpos, size_t pos) {
    T newitem = h[pos];
    while (pos > startpos) {
        size_t parentpos = (pos - 1) >> 1;
        T parent = h[parentpos];
        if (newitem < parent) { h[pos] = parent; pos = parentpos; continue; }
        break;
    }
    h[pos] = newitem;
}
template <class T> static inline void py_siftup(const PyList<T>& h, size_t pos) {
    size_t endpos = h.size(), startpos = pos;
    T newitem = h[pos];
    size_t childpos = 2 * pos + 1;
    while (childpos < endpos) {
        size_t rightpos = childpos + 1;
        if (rightpos < endpos && !(h[childpos] < h[rightpos])) childpos = rightpos;
        h[pos] = h[childpos];
        pos = childpos;
        childpos = 2 * pos + 1;
    }
    h[pos] = newitem;
    py_siftdown(h, startpos, pos);
}
template <class T> static inline void py_heappush(const PyList<T>& h, const T& x) { h.push_back(x); py_siftdown(h, 0, h.size() - 1); }
template <class T> static inline T py_heappop(const PyList<T>& h) {
    if (h.empty()) py_throw("IndexError", "index out of range");
    T last = h[h.size() - 1];
    h.erase(h.end() - 1);
    if (h.empty()) return last;
    T ret = h[0];
    h[0] = last;
    py_siftup(h, 0);
    return ret;
}
template <class T> static inline T py_heapreplace(const PyList<T>& h, const T& x) {
    if (h.empty()) py_throw("IndexError", "index out of range");
    T ret = h[0]; h[0] = x; py_siftup(h, 0); return ret;
}
template <class T> static inline T py_heappushpop(const PyList<T>& h, const T& x) {
    if (!h.empty() && h[0] < x) { T ret = h[0]; h[0] = x; py_siftup(h, 0); return ret; }
    return x;
}
template <class T> static inline void py_heapify(const PyList<T>& h) { size_t n = h.size(); for (size_t i = n / 2; i-- > 0;) py_siftup(h, i); }
template <class T> static inline PyList<T> py_nsmallest(long long n, const PyList<T>& xs) {
    std::vector<T> r(xs.begin(), xs.end());
    std::stable_sort(r.begin(), r.end());
    if (n < 0) n = 0;
    if ((size_t)n < r.size()) r.resize((size_t)n);
    return PyList<T>(std::move(r));
}
template <class T> static inline PyList<T> py_nlargest(long long n, const PyList<T>& xs) {
    std::vector<T> r(xs.begin(), xs.end());
    std::stable_sort(r.begin(), r.end(), [](const T& a, const T& b) { return b < a; });
    if (n < 0) n = 0;
    if ((size_t)n < r.size()) r.resize((size_t)n);
    return PyList<T>(std::move(r));
}

template <class K, class V> static inline PyDict<K, V> py_dict_plain(const PyDict<K, V>& m) {
    PyDict<K, V> r;
    for (const auto& kv : m) r[kv.first] = kv.second;
    return r;
}
template <class T> static inline PyList<PyVT<T>> py_zip_star(const PyList<PyList<T>>& m) {
    std::vector<PyVT<T>> r;
    if (m.size() == 0) return PyList<PyVT<T>>(std::move(r));
    size_t n = m[0].size();
    for (size_t i = 1; i < m.size(); i++) n = std::min(n, m[i].size());
    for (size_t j = 0; j < n; j++) {
        std::vector<T> col;
        for (size_t i = 0; i < m.size(); i++) col.push_back(m[i][j]);
        r.push_back(PyVT<T>(std::move(col)));
    }
    return PyList<PyVT<T>>(std::move(r));
}
template <class T, class F> static inline T py_reduce(const PyList<T>& xs, F f) {
    if (xs.size() == 0) py_throw("TypeError", "reduce() of empty iterable with no initial value");
    T acc = xs[0];
    for (size_t i = 1; i < xs.size(); i++) acc = f(acc, xs[i]);
    return acc;
}
template <class T, class A, class F> static inline A py_reduce_init(const PyList<T>& xs, A acc, F f) {
    for (size_t i = 0; i < xs.size(); i++) acc = f(acc, xs[i]);
    return acc;
}

// ---------- générateurs (coroutines C++20) : passage unique, évaluation paresseuse ----------
template <class T> struct PyGen {
    struct promise_type;
    using H = std::coroutine_handle<promise_type>;
    struct promise_type {
        T value{};
        std::exception_ptr exc;
        PyGen get_return_object() { return PyGen(H::from_promise(*this)); }
        std::suspend_always initial_suspend() noexcept { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        std::suspend_always yield_value(T v) { value = std::move(v); return {}; }
        void return_void() {}
        void unhandled_exception() { exc = std::current_exception(); }
    };
    struct Owner { H h; explicit Owner(H hh) : h(hh) {} ~Owner() { if (h) h.destroy(); } Owner(const Owner&) = delete; };
    std::shared_ptr<Owner> o;
    explicit PyGen(H h) : o(std::make_shared<Owner>(h)) {}
    bool advance() const {  // exécute jusqu'au prochain yield ; false quand le générateur est épuisé
        H h = o->h;
        if (h.done()) return false;
        h.resume();
        if (h.promise().exc) { auto e = h.promise().exc; h.promise().exc = nullptr; std::rethrow_exception(e); }
        return !h.done();
    }
    struct iterator {
        const PyGen* g; bool ok;
        T& operator*() const { return g->o->h.promise().value; }
        iterator& operator++() { ok = g->advance(); return *this; }
        bool operator!=(const iterator&) const { return ok; }
    };
    iterator begin() const { return iterator{this, advance()}; }
    iterator end() const { return iterator{this, false}; }
};
template <class T> static inline PyList<T> py_gen_list(const PyGen<T>& g) { std::vector<T> r; for (auto x : g) r.push_back(x); return PyList<T>(std::move(r)); }
template <class T> static inline T py_gen_next(const PyGen<T>& g) {
    if (!g.advance()) py_throw("StopIteration", "");
    return g.o->h.promise().value;
}
template <class T> static inline T py_gen_next_default(const PyGen<T>& g, const T& d) {
    if (!g.advance()) return d;
    return g.o->h.promise().value;
}
template <class T> static inline PyList<T> py_gen_take(const PyGen<T>& g, long long n) {
    std::vector<T> r;
    while ((long long)r.size() < n && g.advance()) r.push_back(g.o->h.promise().value);
    return PyList<T>(std::move(r));
}

// ---------- bisect ----------
template <class T, class X> static inline long long py_bisect_left(const PyList<T>& xs, const X& x) { return (long long)(std::lower_bound(xs.begin(), xs.end(), (T)x) - xs.begin()); }
template <class T, class X> static inline long long py_bisect_right(const PyList<T>& xs, const X& x) { return (long long)(std::upper_bound(xs.begin(), xs.end(), (T)x) - xs.begin()); }
template <class T, class X> static inline void py_insort_left(const PyList<T>& xs, const X& x) { xs.insert(xs.begin() + py_bisect_left(xs, x), (T)x); }
template <class T, class X> static inline void py_insort_right(const PyList<T>& xs, const X& x) { xs.insert(xs.begin() + py_bisect_right(xs, x), (T)x); }

// ---------- itertools (résultats construits d'un coup, dans l'ordre exact d'itertools) ----------
template <class A, class B> static inline PyList<std::tuple<A, B>> py_product2(const PyList<A>& a, const PyList<B>& b) {
    std::vector<std::tuple<A, B>> r;
    for (const auto& x : a) for (const auto& y : b) r.emplace_back(x, y);
    return PyList<std::tuple<A, B>>(std::move(r));
}
template <class A, class B, class C> static inline PyList<std::tuple<A, B, C>> py_product3(const PyList<A>& a, const PyList<B>& b, const PyList<C>& c) {
    std::vector<std::tuple<A, B, C>> r;
    for (const auto& x : a) for (const auto& y : b) for (const auto& z : c) r.emplace_back(x, y, z);
    return PyList<std::tuple<A, B, C>>(std::move(r));
}
template <class T> static inline PyList<PyVT<T>> py_product_rep(const PyList<T>& xs, long long k) {
    std::vector<PyVT<T>> out;
    std::vector<T> cur;
    std::function<void()> rec = [&]() {
        if ((long long)cur.size() == k) { out.push_back(PyVT<T>(cur)); return; }
        for (size_t i = 0; i < xs.size(); i++) { cur.push_back(xs[i]); rec(); cur.pop_back(); }
    };
    rec();
    return PyList<PyVT<T>>(std::move(out));
}
template <class T> static inline PyList<PyVT<T>> py_permutations_vec(const PyList<T>& xs, long long r) {
    size_t n = xs.size();
    if (r < 0) r = (long long)n;
    std::vector<PyVT<T>> out;
    if ((size_t)r > n) return PyList<PyVT<T>>(std::move(out));
    std::vector<bool> used(n, false);
    std::vector<T> cur;
    std::function<void()> rec = [&]() {
        if ((long long)cur.size() == r) { out.push_back(PyVT<T>(cur)); return; }
        for (size_t i = 0; i < n; i++) if (!used[i]) { used[i] = true; cur.push_back(xs[i]); rec(); cur.pop_back(); used[i] = false; }
    };
    rec();
    return PyList<PyVT<T>>(std::move(out));
}
template <class T> static inline PyList<PyVT<T>> py_combinations_vec(const PyList<T>& xs, long long r) {
    size_t n = xs.size();
    std::vector<PyVT<T>> out;
    if (r < 0 || (size_t)r > n) return PyList<PyVT<T>>(std::move(out));
    std::vector<T> cur;
    std::function<void(size_t)> rec = [&](size_t start) {
        if ((long long)cur.size() == r) { out.push_back(PyVT<T>(cur)); return; }
        for (size_t i = start; i < n; i++) { cur.push_back(xs[i]); rec(i + 1); cur.pop_back(); }
    };
    rec(0);
    return PyList<PyVT<T>>(std::move(out));
}
template <class T> static inline PyList<PyVT<T>> py_combinations_with_replacement_vec(const PyList<T>& xs, long long r) {
    size_t n = xs.size();
    std::vector<PyVT<T>> out;
    if (r < 0 || (n == 0 && r > 0)) return PyList<PyVT<T>>(std::move(out));
    std::vector<T> cur;
    std::function<void(size_t)> rec = [&](size_t start) {
        if ((long long)cur.size() == r) { out.push_back(PyVT<T>(cur)); return; }
        for (size_t i = start; i < n; i++) { cur.push_back(xs[i]); rec(i); cur.pop_back(); }
    };
    rec(0);
    return PyList<PyVT<T>>(std::move(out));
}
template <class T, size_t> using PyRep = T;
template <class T, size_t... I> static inline auto py_vt_tuple_from(const PyVT<T>& v, std::index_sequence<I...>) { return std::tuple<PyRep<T, I>...>(v[I]...); }
template <size_t N, class T> static inline auto py_vt_to_tuples(const PyList<PyVT<T>>& xs) {
    using Tup = decltype(py_vt_tuple_from(std::declval<PyVT<T>>(), std::make_index_sequence<N>{}));
    std::vector<Tup> r;
    for (const auto& v : xs) r.push_back(py_vt_tuple_from(v, std::make_index_sequence<N>{}));
    return PyList<Tup>(std::move(r));
}
template <class T, class F> static inline PyList<T> py_accumulate(const PyList<T>& xs, F f) {
    std::vector<T> r;
    for (size_t i = 0; i < xs.size(); i++) r.push_back(i == 0 ? xs[0] : f(r.back(), xs[i]));
    return PyList<T>(std::move(r));
}
template <class T, class F> static inline PyList<T> py_accumulate_init(const PyList<T>& xs, T init, F f) {
    std::vector<T> r{init};
    for (size_t i = 0; i < xs.size(); i++) r.push_back(f(r.back(), xs[i]));
    return PyList<T>(std::move(r));
}
template <class L> static inline auto py_flatten(const PyList<L>& xs) {
    using T = typename L::value_type;
    std::vector<T> r;
    for (const auto& l : xs) for (const auto& x : l) r.push_back(x);
    return PyList<T>(std::move(r));
}

// ---------- entrées / sorties standard ----------
static inline std::string py_stdin_read() { return std::string((std::istreambuf_iterator<char>(std::cin)), std::istreambuf_iterator<char>()); }
static inline std::string py_stdin_readline() {
    std::string line;
    if (!std::getline(std::cin, line)) return "";
    if (!std::cin.eof()) line += "\n";
    return line;
}
static inline PyList<std::string> py_stdin_readlines() {
    std::vector<std::string> r;
    while (true) { std::string l = py_stdin_readline(); if (l.empty()) break; r.push_back(l); }
    return PyList<std::string>(std::move(r));
}
static inline void py_stdout_write(const std::string& s) { std::cout << s; }
static inline void py_stderr_write(const std::string& s) { std::cerr << s; }
static inline void py_stdout_flush() { std::cout.flush(); }
template <class K, class V> static inline PyDict<K, V> py_dict_merge(const PyDict<K, V>& a, const PyDict<K, V>& b) {
    PyDict<K, V> r;
    for (const auto& kv : a) r[kv.first] = kv.second;
    for (const auto& kv : b) r[kv.first] = kv.second;
    return r;
}

// ---------- math : domaines et dépassements comme en Python ----------
static inline double py_sqrt(double x) { if (x < 0) py_throw("ValueError", "math domain error"); return std::sqrt(x); }
static inline double py_log(double x) { if (x <= 0) py_throw("ValueError", "math domain error"); return std::log(x); }
static inline double py_log2(double x) { if (x <= 0) py_throw("ValueError", "math domain error"); return std::log2(x); }
static inline double py_log10(double x) { if (x <= 0) py_throw("ValueError", "math domain error"); return std::log10(x); }
static inline double py_log1p(double x) { if (x <= -1) py_throw("ValueError", "math domain error"); return std::log1p(x); }
static inline double py_asin(double x) { if (x < -1 || x > 1) py_throw("ValueError", "math domain error"); return std::asin(x); }
static inline double py_acos(double x) { if (x < -1 || x > 1) py_throw("ValueError", "math domain error"); return std::acos(x); }
static inline double py_exp(double x) { double r = std::exp(x); if (std::isinf(r) && !std::isinf(x)) py_throw("OverflowError", "math range error"); return r; }
static inline double py_expm1(double x) { double r = std::expm1(x); if (std::isinf(r) && !std::isinf(x)) py_throw("OverflowError", "math range error"); return r; }
static inline double py_fpow(double a, double b) {  // opérateur ** entre flottants
    if (a == 0.0 && b < 0) py_throw("ZeroDivisionError", "0.0 cannot be raised to a negative power");
    if (a < 0 && b != std::floor(b) && !std::isinf(b)) py_throw("ValueError", "negative number raised to a fractional power gives a complex result (not supported)");
    double r = std::pow(a, b);
    if (std::isinf(r) && !std::isinf(a) && !std::isinf(b)) py_throw("OverflowError", "(34, 'Result too large')");
    return r;
}
static inline double py_mpow(double a, double b) {  // math.pow
    if (a == 0.0 && b < 0) py_throw("ValueError", "math domain error");
    if (a < 0 && b != std::floor(b) && !std::isinf(b)) py_throw("ValueError", "math domain error");
    double r = std::pow(a, b);
    if (std::isinf(r) && !std::isinf(a) && !std::isinf(b)) py_throw("OverflowError", "math range error");
    return r;
}
static inline bool py_isclose(double a, double b) {
    if (a == b) return true;
    if (std::isinf(a) || std::isinf(b)) return false;
    double d = std::fabs(a - b);
    return d <= std::max(1e-9 * std::max(std::fabs(a), std::fabs(b)), 0.0);
}
static inline long long py_comb(long long n, long long k) {
    if (n < 0 || k < 0) py_throw("ValueError", "n and k must be non-negative integers");
    if (k > n) return 0;
    if (k > n - k) k = n - k;
    long long r = 1;
    for (long long i = 1; i <= k; i++) r = py_mul(r, n - k + i) / i;
    return r;
}
static inline long long py_perm(long long n, long long k) {
    if (n < 0 || k < 0) py_throw("ValueError", "n and k must be non-negative integers");
    if (k > n) return 0;
    long long r = 1;
    for (long long i = 0; i < k; i++) r = py_mul(r, n - i);
    return r;
}
template <class V> static inline auto py_prod(const V& v) {
    typename V::value_type p = 1;
    for (const auto& x : v) { if constexpr (std::is_same<typename V::value_type, long long>::value) p = py_mul(p, x); else p *= x; }
    return p;
}
// ---------- Counter / defaultdict ----------
template <class K> static inline long long py_cnt_at(const PyDict<K, long long>& d, const K& k) { return d.count(k) ? d.at(k) : 0; }
template <class K> static inline PyDict<K, long long> py_counter_from(const PyList<K>& xs) {
    PyDict<K, long long> d = py_dnew<K, long long>(2, "");
    for (const auto& x : xs) d[x] += 1;
    return d;
}
template <class K> static inline void py_counter_update(const PyDict<K, long long>& d, const PyList<K>& xs) { for (const auto& x : xs) d[x] += 1; }
template <class K> static inline void py_counter_update(const PyDict<K, long long>& d, const PyDict<K, long long>& o) {
    std::vector<std::pair<K, long long>> t(o.begin(), o.end());
    for (auto& kv : t) d[kv.first] += kv.second;
}
template <class K> static inline PyList<std::tuple<K, long long>> py_most_common(const PyDict<K, long long>& d, long long n) {
    std::vector<std::tuple<K, long long>> r;
    for (const auto& kv : d) r.emplace_back(kv.first, kv.second);
    std::stable_sort(r.begin(), r.end(), [](const auto& a, const auto& b) { return std::get<1>(b) < std::get<1>(a); });
    if (n >= 0 && (size_t)n < r.size()) r.resize((size_t)n);
    return PyList<std::tuple<K, long long>>(std::move(r));
}
template <class K> static inline long long py_counter_total(const PyDict<K, long long>& d) { long long s = 0; for (const auto& kv : d) s += kv.second; return s; }
template <class K> static inline PyList<K> py_counter_elements(const PyDict<K, long long>& d) {
    std::vector<K> r;
    for (const auto& kv : d) for (long long i = 0; i < kv.second; i++) r.push_back(kv.first);
    return PyList<K>(std::move(r));
}
template <class K> static inline std::string py_counter_repr(const PyDict<K, long long>& d) {
    if (d.size() == 0) return "Counter()";
    std::string r = "Counter({";
    bool first = true;
    for (const auto& kv : py_most_common(d, -1)) { if (!first) r += ", "; first = false; r += py_repr(std::get<0>(kv)) + ": " + py_repr(std::get<1>(kv)); }
    return r + "})";
}
template <class K, class V> static inline std::string py_ddict_repr(const PyDict<K, V>& d, const std::string& factory) {
    return "defaultdict(" + factory + ", " + py_str(d) + ")";
}
template <class K, class V> static inline std::string py_odict_repr(const PyDict<K, V>& d) {
    if (d.size() == 0) return "OrderedDict()";
    std::string r = "OrderedDict([";
    bool first = true;
    for (const auto& kv : d) { if (!first) r += ", "; first = false; r += "(" + py_repr(kv.first) + ", " + py_repr(kv.second) + ")"; }
    return r + "])";
}
template <class K, class V> static inline void py_move_to_end(const PyDict<K, V>& d, const K& k, bool last) {
    V v = d.at(k);
    d.erase(k);
    if (last) { d[k] = v; return; }
    std::vector<std::pair<K, V>> rest(d.begin(), d.end());
    d.clear();
    d[k] = v;
    for (auto& kv : rest) d[kv.first] = kv.second;
}
template <class K, class V> static inline std::tuple<K, V> py_popitem_at(const PyDict<K, V>& d, bool last) {
    if (d.size() == 0) py_throw("KeyError", "'dictionary is empty'");
    auto kv = last ? *(d.end() - 1) : *d.begin();
    d.erase(kv.first);
    return std::tuple<K, V>(kv.first, kv.second);
}
'''

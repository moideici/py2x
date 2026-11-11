"""Émulation Python du set d'entiers de CPython 3.11 (banc de mise au point : comparée à set() réel)."""
import random
LP = 9
M64 = (1 << 64) - 1


class S:
    def __init__(s):
        s.key = [0] * 8; s.hash = [0] * 8; s.st = [0] * 8; s.mask = 7; s.fill = 0; s.used = 0; s.finger = 0

    @staticmethod
    def hh(k): return -2 if k == -1 else k

    def lookup(s, key, h):
        i = (h & M64) & s.mask; perturb = h & M64
        while True:
            idx = i; probes = LP if i + LP <= s.mask else 0
            while True:
                if s.st[idx] == 0: return -1
                if s.st[idx] == 1 and s.hash[idx] == h and s.key[idx] == key: return idx
                idx += 1
                if probes == 0: break
                probes -= 1
            perturb >>= 5
            i = ((i * 5 + 1 + perturb) & M64) & s.mask

    def add(s, key):
        h = s.hh(key)
        i = (h & M64) & s.mask; perturb = h & M64; free = -1; empty = -1
        while empty < 0:
            idx = i; probes = LP if i + LP <= s.mask else 0
            while True:
                if s.st[idx] == 0: empty = idx; break
                if s.st[idx] == 1 and s.hash[idx] == h and s.key[idx] == key: return False
                if s.st[idx] == 2: free = idx
                idx += 1
                if probes == 0: break
                probes -= 1
            if empty >= 0: break
            perturb >>= 5
            i = ((i * 5 + 1 + perturb) & M64) & s.mask
        if free >= 0:
            s.used += 1; s.key[free] = key; s.hash[free] = h; s.st[free] = 1; return True
        s.fill += 1; s.used += 1
        s.key[empty] = key; s.hash[empty] = h; s.st[empty] = 1
        if s.fill * 5 < s.mask * 3: return True
        s.resize(s.used * 2 if s.used > 50000 else s.used * 4)
        return True

    @staticmethod
    def ins(nk, nh, ns, m, key, h):
        i = (h & M64) & m; perturb = h & M64
        while True:
            if ns[i] == 0: nk[i] = key; nh[i] = h; ns[i] = 1; return
            if i + LP <= m:
                for j in range(1, LP + 1):
                    if ns[i + j] == 0: nk[i + j] = key; nh[i + j] = h; ns[i + j] = 1; return
            perturb >>= 5
            i = ((i * 5 + 1 + perturb) & M64) & m

    def resize(s, minused):
        n = 8
        while n <= minused: n <<= 1
        nk = [0] * n; nh = [0] * n; ns = [0] * n
        for i in range(len(s.st)):
            if s.st[i] == 1: s.ins(nk, nh, ns, n - 1, s.key[i], s.hash[i])
        s.key, s.hash, s.st = nk, nh, ns; s.mask = n - 1; s.fill = s.used

    def discard(s, key):
        i = s.lookup(key, s.hh(key))
        if i < 0: return False
        s.st[i] = 2; s.hash[i] = -1; s.used -= 1
        return True

    def items(s): return [s.key[i] for i in range(len(s.st)) if s.st[i] == 1]

    def pop(s):
        i = s.finger & s.mask
        while s.st[i] != 1:
            i += 1
            if i > s.mask: i = 0
        k = s.key[i]; s.st[i] = 2; s.hash[i] = -1; s.used -= 1; s.finger = i + 1
        return k

    def merge(s, o):
        if o is s or o.used == 0: return
        if (s.fill + o.used) * 5 >= s.mask * 3: s.resize((s.used + o.used) * 2)
        if s.fill == 0 and s.mask == o.mask and o.fill == o.used:
            for i in range(o.mask + 1):
                if o.st[i] == 1: s.key[i] = o.key[i]; s.hash[i] = o.hash[i]; s.st[i] = 1
            s.fill = o.fill; s.used = o.used; return
        if s.fill == 0:
            s.fill = s.used = o.used
            for i in range(len(o.st)):
                if o.st[i] == 1: s.ins(s.key, s.hash, s.st, s.mask, o.key[i], o.hash[i])
            return
        for i in range(len(o.st)):
            if o.st[i] == 1: s.add(o.key[i])

    def copy(s):
        r = S(); r.merge(s); return r

    def shrink(s):
        if s.fill - s.used > s.mask // 4: s.resize(s.used * 2 if s.used > 50000 else s.used * 4)


def of(xs):
    r = S()
    for x in xs: r.add(x)
    return r


def inter(a, b):
    r = S()
    it, chk = (a, b) if b.used > a.used else (b, a)
    for x in it.items():
        if chk.lookup(x, chk.hh(x)) >= 0: r.add(x)
    return r


def diff(a, b):
    if (a.used >> 2) > b.used:
        r = a.copy()
        for x in b.items(): r.discard(x)
        r.shrink(); return r
    r = S()
    for x in a.items():
        if b.lookup(x, b.hh(x)) < 0: r.add(x)
    return r


def symdiff(a, b):
    r = b.copy()
    for x in a.items():
        if not r.discard(x): r.add(x)
    return r


def val(r):
    k = r.randrange(6)
    if k == 0: return r.randint(-5, 5)
    if k == 1: return r.randint(0, 40)
    if k == 2: return r.randint(0, 1000) * 8
    if k == 3: return -r.randint(1, 300)
    if k == 4: return r.randint(0, 3) * 2 ** r.randint(0, 40)
    return r.randint(-10 ** 6, 10 ** 6)


def trial(seed):
    r = random.Random(seed)
    A, B = S(), of([1, 2, 3])
    a, b = set(), {1, 2, 3}
    log = []
    for step in range(120):
        v = val(r); op = r.randrange(14)
        if op <= 3: A.add(v); a.add(v); log.append(f"add {v}")
        elif op == 4: A.discard(v); a.discard(v); log.append(f"discard {v}")
        elif op == 5: B.add(v); b.add(v); log.append(f"b.add {v}")
        elif op == 6:
            if a: x = A.pop(); y = a.pop(); log.append("pop")
            if a and x != y: return f"pop {x} {y}", log
        elif op == 7: A.merge(B); a |= b; log.append("|=")
        elif op == 8: t = inter(A, B); A.key, A.hash, A.st, A.mask, A.fill, A.used = t.key, t.hash, t.st, t.mask, t.fill, t.used; a &= b; log.append("&=")
        elif op == 9:
            if A is B: pass
            for x in B.items(): A.discard(x)
            A.shrink(); a -= b; log.append("-=")
        elif op == 10:
            for x in B.items():
                if not A.discard(x): A.add(x)
            a ^= b; log.append("^=")
        elif op == 11:
            T = A.copy(); A2 = S(); A2.merge(T)
            xs = sorted(A.items())[::2] + []
            A = of(xs); a = set(xs); one = of([v]); A = A.copy(); A.merge(one); a = set(sorted(a)) | {v}; log.append("rebuild")
            # NB : set(sorted(a)[::2]) | {v}
        elif op == 12:
            ys = [v, val(r), val(r)]
            for y in ys: A.add(y); a.add(y)
            log.append("update")
        else:
            res = [A.items(), list(a)]
            if res[0] != res[1]: return f"list mismatch at step {step}", log
            for nm, f1, f2 in (("|", lambda: A.copy().merge(B) or None, None),):
                pass
            U = A.copy(); U.merge(B)
            if U.items() != list(a | b): return "union", log
            if inter(A, B).items() != list(a & b): return "inter", log
            if diff(A, B).items() != list(a - b): return "diff", log
            if symdiff(A, B).items() != list(a ^ b): return "symdiff", log
        if A.items() != list(a): return f"mismatch after {log[-1]}", log
    return None


if __name__ == "__main__":
    bad = 0
    for sd in range(3000):
        r = trial(sd)
        if r:
            print(sd, r[0], r[1][-12:]); bad += 1
            if bad > 5: break
    print("bad", bad)

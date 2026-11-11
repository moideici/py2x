"""Module `random` : générateur Mersenne Twister de CPython 3.11, écrit en Python typé et transpilé comme du code utilisateur.
Mêmes séquences que CPython pour random.seed(<int>) : random(), randint(), randrange(), choice(), shuffle(), sample(), choices(),
uniform(), gauss(), getrandbits()."""

PRELUDE = '''
import math
from typing import Optional


class PyRandom:
    def __init__(self, seed: int = 5489) -> None:
        self.mt: list[int] = [0] * 624
        self.index = 625
        self.gauss_next: Optional[float] = None
        self.seed(seed)

    def init_genrand(self, s: int) -> None:
        mt = self.mt
        mt[0] = s & 4294967295
        for i in range(1, 624):
            mt[i] = (1812433253 * (mt[i - 1] ^ (mt[i - 1] >> 30)) + i) & 4294967295

    def seed(self, a: int) -> None:
        n = abs(a)
        key: list[int] = []
        while n > 0:
            key.append(n & 4294967295)
            n >>= 32
        if not key:
            key.append(0)
        self.init_genrand(19650218)
        mt = self.mt
        i = 1
        j = 0
        k = 624 if 624 > len(key) else len(key)
        while k > 0:
            mt[i] = ((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1664525)) + key[j] + j) & 4294967295
            i += 1
            j += 1
            if i >= 624:
                mt[0] = mt[623]
                i = 1
            if j >= len(key):
                j = 0
            k -= 1
        k = 623
        while k > 0:
            mt[i] = ((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1566083941)) - i) & 4294967295
            i += 1
            if i >= 624:
                mt[0] = mt[623]
                i = 1
            k -= 1
        mt[0] = 2147483648
        self.index = 624
        self.gauss_next = None

    def generate(self) -> None:
        mt = self.mt
        for kk in range(624):
            y = (mt[kk] & 2147483648) | (mt[(kk + 1) % 624] & 2147483647)
            v = mt[(kk + 397) % 624] ^ (y >> 1)
            if y & 1:
                v ^= 2567483615
            mt[kk] = v
        self.index = 0

    def next32(self) -> int:
        if self.index >= 624:
            self.generate()
        y = self.mt[self.index]
        self.index += 1
        y ^= y >> 11
        y ^= (y << 7) & 2636928640
        y ^= (y << 15) & 4022730752
        y ^= y >> 18
        return y & 4294967295

    def random(self) -> float:
        a = self.next32() >> 5
        b = self.next32() >> 6
        return (a * 67108864.0 + b) * (1.0 / 9007199254740992.0)

    def getrandbits(self, k: int) -> int:
        if k < 0 or k > 63:
            raise ValueError("getrandbits: number of bits must be between 0 and 63 in this translation")
        if k == 0:
            return 0
        if k <= 32:
            return self.next32() >> (32 - k)
        lo = self.next32()
        hi = self.next32() >> (64 - k)
        return lo | (hi << 32)

    def randbelow(self, n: int) -> int:
        k = n.bit_length()
        r = self.getrandbits(k)
        while r >= n:
            r = self.getrandbits(k)
        return r

    def randrange(self, start: int, stop: Optional[int] = None, step: int = 1) -> int:
        if stop is None:
            if start > 0:
                return self.randbelow(start)
            raise ValueError("empty range for randrange()")
        width = stop - start
        if step == 1:
            if width > 0:
                return start + self.randbelow(width)
            raise ValueError(f"empty range for randrange() ({start}, {stop}, {width})")
        if step > 0:
            n = (width + step - 1) // step
        elif step < 0:
            n = (width + step + 1) // step
        else:
            raise ValueError("zero step for randrange()")
        if n <= 0:
            raise ValueError("empty range for randrange()")
        return start + step * self.randbelow(n)

    def randint(self, a: int, b: int) -> int:
        return self.randrange(a, b + 1)

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self.random()

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        z = self.gauss_next
        self.gauss_next = None
        if z is None:
            x2pi = self.random() * 6.283185307179586
            g2rad = math.sqrt(-2.0 * math.log(1.0 - self.random()))
            z = math.cos(x2pi) * g2rad
            self.gauss_next = math.sin(x2pi) * g2rad
        return mu + z * sigma

    def expovariate(self, lambd: float) -> float:
        return -math.log(1.0 - self.random()) / lambd

    def sample_idx(self, n: int, k: int) -> list[int]:
        if k < 0 or k > n:
            raise ValueError("Sample larger than population or is negative")
        result: list[int] = []
        setsize = 21
        if k > 5:
            setsize += 4 ** math.ceil(math.log(k * 3, 4))
        if n <= setsize:
            pool = list(range(n))
            for i in range(k):
                j = self.randbelow(n - i)
                result.append(pool[j])
                pool[j] = pool[n - i - 1]
        else:
            selected: set[int] = set()
            for i in range(k):
                j = self.randbelow(n)
                while j in selected:
                    j = self.randbelow(n)
                selected.add(j)
                result.append(j)
        return result

    def choices_idx(self, n: int, k: int) -> list[int]:
        return [int(self.random() * n) for _ in range(k)]

    def choices_weighted_idx(self, weights: list[float], k: int) -> list[int]:
        cum: list[float] = []
        acc = 0.0
        for w in weights:
            acc += w
            cum.append(acc)
        total = cum[-1] + 0.0
        out: list[int] = []
        for _ in range(k):
            x = self.random() * total
            lo = 0
            hi = len(cum) - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if x < cum[mid]:
                    hi = mid
                else:
                    lo = mid + 1
            out.append(lo)
        return out


py_rng = PyRandom(5489)


def random_seed(a: int) -> None:
    py_rng.seed(a)


def random_random() -> float:
    return py_rng.random()


def random_randint(a: int, b: int) -> int:
    return py_rng.randint(a, b)


def random_randrange(start: int, stop: Optional[int] = None, step: int = 1) -> int:
    return py_rng.randrange(start, stop, step)


def random_uniform(a: float, b: float) -> float:
    return py_rng.uniform(a, b)


def random_gauss(mu: float = 0.0, sigma: float = 1.0) -> float:
    return py_rng.gauss(mu, sigma)


def random_expovariate(lambd: float) -> float:
    return py_rng.expovariate(lambd)


def random_getrandbits(k: int) -> int:
    return py_rng.getrandbits(k)
'''

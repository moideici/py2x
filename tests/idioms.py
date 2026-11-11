"""Banc d'idiomes : petits fragments Python courants ; indique lesquels le convertisseur accepte (conversion seulement, sans compilation).

  python tests/idioms.py            # liste les refus
  python tests/idioms.py --all      # liste tout
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from py2x import Unsupported, transpile  # noqa: E402

IDIOMS = {
    "print(*xs)": "def f(xs: list[int]) -> None:\n    print(*xs)\n    print(*xs, sep=', ')\n",
    "*args": "def total(*nums: int) -> int:\n    return sum(nums)\n\ndef f() -> int:\n    return total(1, 2, 3)\n",
    "call *list": "def add(a: int, b: int) -> int:\n    return a + b\n\ndef f(xs: list[int]) -> int:\n    return add(*xs)\n",
    "kw-only default": "def f(a: int, b: int = 2, *, c: int = 3) -> int:\n    return a + b + c\n",
    "for-else": "def f(n: int) -> bool:\n    for i in range(2, n):\n        if n % i == 0:\n            break\n    else:\n        return True\n    return False\n",
    "while-else": "def f(n: int) -> int:\n    while n > 0:\n        n -= 1\n    else:\n        return 7\n    return 0\n",
    "star unpack": "def f(xs: list[int]) -> int:\n    a, *rest = xs\n    return a + len(rest)\n",
    "swap/index": "def f(xs: list[int]) -> None:\n    xs[0], xs[-1] = xs[-1], xs[0]\n",
    "walrus": "def f(xs: list[int]) -> int:\n    if (n := len(xs)) > 2:\n        return n\n    return 0\n",
    "bisect": "import bisect\n\ndef f(xs: list[int]) -> int:\n    bisect.insort(xs, 5)\n    return bisect.bisect_left(xs, 5)\n",
    "from bisect": "from bisect import bisect_right\n\ndef f(xs: list[int]) -> int:\n    return bisect_right(xs, 5)\n",
    "dict.fromkeys": "def f(ks: list[str]) -> dict[str, int]:\n    return dict.fromkeys(ks, 0)\n",
    "dict merge |": "def f(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:\n    return a | b\n",
    "dict ** merge": "def f(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:\n    return {**a, **b}\n",
    "list unpack in literal": "def f(a: list[int], b: list[int]) -> list[int]:\n    return [*a, *b]\n",
    "lru_cache": "from functools import lru_cache\n\n@lru_cache(maxsize=None)\ndef fib(n: int) -> int:\n    return n if n < 2 else fib(n - 1) + fib(n - 2)\n",
    "cache": "from functools import cache\n\n@cache\ndef fib(n: int) -> int:\n    return n if n < 2 else fib(n - 1) + fib(n - 2)\n",
    "itertools.product": "import itertools\n\ndef f() -> list[tuple[int, int]]:\n    return list(itertools.product([1, 2], [3, 4]))\n",
    "itertools.permutations": "from itertools import permutations\n\ndef f() -> int:\n    return len(list(permutations([1, 2, 3])))\n",
    "itertools.combinations": "from itertools import combinations\n\ndef f(xs: list[int]) -> int:\n    return sum(a * b for a, b in combinations(xs, 2))\n",
    "itertools.accumulate": "from itertools import accumulate\n\ndef f(xs: list[int]) -> list[int]:\n    return list(accumulate(xs))\n",
    "itertools.chain": "from itertools import chain\n\ndef f(a: list[int], b: list[int]) -> list[int]:\n    return list(chain(a, b))\n",
    "random": "import random\n\ndef f() -> int:\n    random.seed(1)\n    return random.randint(1, 6)\n",
    "random.choice/shuffle": "import random\n\ndef f(xs: list[int]) -> int:\n    random.shuffle(xs)\n    return random.choice(xs)\n",
    "math.comb": "import math\n\ndef f() -> int:\n    return math.comb(5, 2) + math.prod([1, 2, 3]) + math.perm(4, 2)\n",
    "math.hypot/isclose": "import math\n\ndef f() -> bool:\n    return math.isclose(math.hypot(3.0, 4.0), 5.0)\n",
    "math.floor int": "import math\n\ndef f(x: float) -> int:\n    return math.floor(x) + math.ceil(x) + math.trunc(x)\n",
    "sys.stdin.read": "import sys\n\ndef f() -> int:\n    data = sys.stdin.read().split()\n    return len(data)\n",
    "sys.stdin lines": "import sys\n\ndef f() -> int:\n    n = 0\n    for line in sys.stdin:\n        n += len(line.strip())\n    return n\n",
    "input int": "def f() -> int:\n    n = int(input())\n    return n * 2\n",
    "sys.stdout.write": "import sys\n\ndef f() -> None:\n    sys.stdout.write('hi\\n')\n",
    "NamedTuple": "from typing import NamedTuple\n\nclass P(NamedTuple):\n    x: int\n    y: int\n\ndef f() -> int:\n    p = P(1, 2)\n    return p.x + p.y\n",
    "namedtuple unpack": "from typing import NamedTuple\n\nclass P(NamedTuple):\n    x: int\n    y: int\n\ndef f() -> int:\n    a, b = P(1, 2)\n    return a + b\n",
    "dataclass order": "from dataclasses import dataclass\n\n@dataclass(order=True)\nclass P:\n    x: int\n    y: int = 0\n\ndef f() -> bool:\n    return P(1) < P(2)\n",
    "dataclass post_init": "from dataclasses import dataclass\n\n@dataclass\nclass P:\n    x: int\n    y: int = 0\n\n    def __post_init__(self) -> None:\n        self.y = self.x * 2\n",
    "dataclass sorted": "from dataclasses import dataclass\n\n@dataclass(order=True)\nclass P:\n    x: int\n\ndef f(ps: list[P]) -> list[P]:\n    return sorted(ps)\n",
    "sort objects __lt__": "class A:\n    def __init__(self, v: int) -> None:\n        self.v = v\n    def __lt__(self, o: 'A') -> bool:\n        return self.v < o.v\n\ndef f(xs: list[A]) -> list[A]:\n    return sorted(xs)\n",
    "__iter__": "class A:\n    def __init__(self) -> None:\n        self.xs: list[int] = [1]\n    def __iter__(self):\n        return iter(self.xs)\n",
    "__hash__/set of objs": "class A:\n    def __init__(self, v: int) -> None:\n        self.v = v\n\ndef f(a: A) -> int:\n    s = {a}\n    return len(s)\n",
    "generator fn": "def gen(n: int):\n    for i in range(n):\n        yield i\n",
    "generator in for": "def gen(n: int) -> list[int]:\n    return [i for i in range(n)]\n",
    "with open": "def f(p: str) -> int:\n    with open(p) as fh:\n        return len(fh.read())\n",
    "any type": "from typing import Any\n\ndef f(x: Any) -> int:\n    return 1\n",
    "Union": "from typing import Union\n\ndef f(x: Union[int, str]) -> int:\n    return 1\n",
    "global counter": "n = 0\n\ndef f() -> int:\n    global n\n    n += 1\n    return n\n",
    "string % format": "def f(n: int) -> str:\n    return 'n=%d %s' % (n, 'x')\n",
    "str.format": "def f(n: int) -> str:\n    return '{} and {:>4}'.format(n, n)\n",
    "f-string nested spec": "def f(n: int, w: int) -> str:\n    return f'{n:>{w}}'\n",
    "list of lists comp": "def f(n: int) -> list[list[int]]:\n    return [[i * j for j in range(n)] for i in range(n)]\n",
    "nested func": "def f(n: int) -> int:\n    def g(x: int) -> int:\n        return x + n\n    return g(1)\n",
    "closure return": "from typing import Callable\n\ndef make(n: int) -> Callable[[int], int]:\n    def g(x: int) -> int:\n        return x + n\n    return g\n",
    "counter closure nonlocal": "from typing import Callable\n\ndef make() -> Callable[[], int]:\n    c = 0\n    def inc() -> int:\n        nonlocal c\n        c += 1\n        return c\n    return inc\n",
    "int.bit_count": "def f(n: int) -> int:\n    return n.bit_count()\n",
    "str.isidentifier etc": "def f(s: str) -> bool:\n    return s.isalnum() and s.isascii()\n",
    "str.partition": "def f(s: str) -> str:\n    a, _, b = s.partition('=')\n    return b\n",
    "tuple compare": "def f(a: tuple[int, int], b: tuple[int, int]) -> bool:\n    return a < b\n",
    "list of tuples sort": "def f(xs: list[tuple[str, int]]) -> list[tuple[str, int]]:\n    return sorted(xs, key=lambda t: (-t[1], t[0]))\n",
    "max with tuple key": "def f(xs: list[str]) -> str:\n    return max(xs, key=lambda s: (len(s), s))\n",
    "ternary chain": "def f(n: int) -> str:\n    return 'neg' if n < 0 else 'zero' if n == 0 else 'pos'\n",
    "chained cmp": "def f(n: int) -> bool:\n    return 0 < n < 10\n",
    "int division neg": "def f(a: int, b: int) -> int:\n    return a // b + a % b\n",
    "float ops": "def f(a: float) -> float:\n    return a ** 0.5 + abs(a) + round(a, 2)\n",
    "complex": "def f() -> complex:\n    return 1 + 2j\n",
    "bytes": "def f() -> bytes:\n    return b'abc'\n",
    "set ops": "def f(a: set[int], b: set[int]) -> set[int]:\n    return (a | b) - (a & b)\n",
    "frozenset": "def f(xs: list[int]) -> frozenset[int]:\n    return frozenset(xs)\n",
    "try/else": "def f(s: str) -> int:\n    try:\n        n = int(s)\n    except ValueError:\n        return -1\n    else:\n        return n\n",
    "custom exc with fields": "class E(Exception):\n    def __init__(self, code: int) -> None:\n        super().__init__('code')\n        self.code = code\n\ndef f() -> int:\n    try:\n        raise E(3)\n    except E as e:\n        return e.code\n",
    "raise from": "def f() -> None:\n    try:\n        pass\n    except ValueError as e:\n        raise RuntimeError('x') from e\n",
    "assert msg": "def f(n: int) -> None:\n    assert n > 0, 'must be positive'\n",
    "with lock-like (contextmanager)": "class C:\n    def __enter__(self) -> 'C':\n        return self\n    def __exit__(self, *a: object) -> None:\n        pass\n\ndef f() -> None:\n    with C() as c:\n        pass\n",
    "typing List": "from typing import List, Dict, Tuple, Optional\n\ndef f(a: List[int], b: Dict[str, int], c: Tuple[int, int]) -> Optional[int]:\n    return None\n",
    "default None param": "from typing import Optional\n\ndef f(a: Optional[int] = None) -> int:\n    return a if a is not None else 0\n",
    "class default list field": "from dataclasses import dataclass, field\n\n@dataclass\nclass A:\n    xs: list[int] = field(default_factory=list)\n",
    "slots/ClassVar": "from typing import ClassVar\n\nclass A:\n    n: ClassVar[int] = 0\n",
    "__eq__ __hash__": "class A:\n    def __init__(self, v: int) -> None:\n        self.v = v\n    def __eq__(self, o: 'A') -> bool:\n        return self.v == o.v\n    def __hash__(self) -> int:\n        return hash(self.v)\n",
    "hash()": "def f(s: str) -> int:\n    return hash(s)\n",
    "id/type": "def f(x: int) -> str:\n    return str(type(x))\n",
    "getattr": "class A:\n    def __init__(self) -> None:\n        self.v = 1\n\ndef f(a: A) -> int:\n    return getattr(a, 'v')\n",
    "enumerate start": "def f(xs: list[str]) -> list[str]:\n    return [f'{i}:{x}' for i, x in enumerate(xs, 1)]\n",
    "zip 3 / unpack": "def f(a: list[int], b: list[int]) -> int:\n    t = 0\n    for x, y in zip(a, b):\n        t += x * y\n    return t\n",
    "sorted reverse": "def f(xs: list[int]) -> list[int]:\n    return sorted(xs, reverse=True)\n",
    "all/any gen": "def f(xs: list[int]) -> bool:\n    return all(x > 0 for x in xs) and any(x > 5 for x in xs)\n",
    "min/max default": "def f(xs: list[int]) -> int:\n    return max(xs, default=0) + min(xs, default=0)\n",
    "str slicing": "def f(s: str) -> str:\n    return s[::-1] + s[1:3] + s[-2:]\n",
    "join gen": "def f(xs: list[int]) -> str:\n    return ','.join(str(x) for x in xs)\n",
    "dict comprehension": "def f(xs: list[str]) -> dict[str, int]:\n    return {x: len(x) for x in xs}\n",
    "dict items sort": "def f(d: dict[str, int]) -> list[tuple[str, int]]:\n    return sorted(d.items(), key=lambda kv: kv[1])\n",
    "str to list": "def f(s: str) -> list[str]:\n    return list(s)\n",
    "ord/chr": "def f(s: str) -> int:\n    return sum(ord(c) - 96 for c in s)\n",
    "divmod": "def f(a: int, b: int) -> tuple[int, int]:\n    return divmod(a, b)\n",
    "pow 3 args": "def f(a: int, b: int, m: int) -> int:\n    return pow(a, b, m)\n",
    "int(x, base) / bin": "def f(s: str) -> str:\n    return bin(int(s, 2) + 1)\n",
    "list index/count": "def f(xs: list[int]) -> int:\n    return xs.index(3) + xs.count(3)\n",
    "tuple in set": "def f() -> int:\n    s: set[tuple[int, int]] = set()\n    s.add((1, 2))\n    return len(s)\n",
    "deque maxlen/rotate": "from collections import deque\n\ndef f() -> int:\n    d: deque[int] = deque(maxlen=3)\n    d.extend([1, 2, 3, 4])\n    d.rotate(1)\n    return d[0]\n",
    "heapq with objects (tuple)": "import heapq\n\ndef f() -> int:\n    h: list[tuple[int, str]] = []\n    heapq.heappush(h, (2, 'b'))\n    heapq.heappush(h, (1, 'a'))\n    return heapq.heappop(h)[0]\n",
    "matrix transpose zip": "def f(m: list[list[int]]) -> list[list[int]]:\n    return [list(r) for r in zip(*m)]\n",
    "round half even": "def f(x: float) -> int:\n    return round(x)\n",
    "string compare": "def f(a: str, b: str) -> bool:\n    return a < b\n",
    "isinstance builtin": "def f(x: int) -> bool:\n    return isinstance(x, int)\n",
    "nested dict": "def f() -> dict[str, dict[str, int]]:\n    d: dict[str, dict[str, int]] = {}\n    d.setdefault('a', {})['b'] = 1\n    return d\n",
    "list of dict": "def f() -> list[dict[str, int]]:\n    return [{'a': 1}, {'b': 2}]\n",
    "main guard exit": "import sys\n\ndef main() -> int:\n    return 0\n\nif __name__ == '__main__':\n    sys.exit(main())\n",
}


def main():
    show_all = "--all" in sys.argv
    bad = 0
    for name, src in IDIOMS.items():
        try:
            transpile(src, "cpp")
            transpile(src, "kotlin")
            status = "ok"
        except Unsupported as e:
            status, bad = f"REFUS : {str(e)[:110]}", bad + 1
        except Exception as e:  # noqa: BLE001
            status, bad = f"BUG : {type(e).__name__}: {str(e)[:100]}", bad + 1
        if show_all or status != "ok":
            print(f"{name:34} {status}")
    print(f"\n{len(IDIOMS) - bad}/{len(IDIOMS)} idiomes acceptés")


if __name__ == "__main__":
    main()

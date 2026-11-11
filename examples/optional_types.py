from typing import Optional

best = None


def find_first_even(xs: list[int]) -> Optional[int]:
    for x in xs:
        if x % 2 == 0:
            return x
    return None


def describe(x: Optional[int]) -> str:
    if x is None:
        return "nothing"
    return f"value {x + 1}"


def lookup(d: dict[str, int], key: str, default: Optional[int] = None) -> Optional[int]:
    v = d.get(key)
    if v is None:
        return default
    return v * 10


def longest(words: list[str]) -> Optional[str]:
    result: Optional[str] = None
    for w in words:
        if result is None or len(w) > len(result):
            result = w
    return result


def update_best(v: int) -> None:
    global best
    if best is None or v > best:
        best = v


class Item:
    def __init__(self, name: str) -> None:
        self.name = name
        self.parent = None
        self.note = None
        self.size = 0

    def attach(self, parent: "Item") -> None:
        self.parent = parent

    def root(self) -> "Item":
        cur = self
        while cur.parent is not None:
            cur = cur.parent
        return cur

    def label(self) -> str:
        if self.note:
            return self.name + ":" + self.note
        return self.name


def main() -> None:
    print(find_first_even([1, 3, 4, 6]), find_first_even([1, 3]), describe(find_first_even([2])), describe(None))
    d = {"a": 1, "b": 2}
    print(lookup(d, "a"), lookup(d, "z"), lookup(d, "z", 99), d.get("b"), d.get("q"))
    print(longest(["aa", "bbbb", "c"]), longest([]))
    for v in [3, 9, 2, 11, 5]:
        update_best(v)
    print(best)
    opts: list[Optional[int]] = [1, None, 3]
    total = 0
    for o in opts:
        if o is not None:
            total += o
    print(opts, total, opts[1] is None, opts[0] == 1, opts[1] == None, opts[0] != None)
    x: Optional[int] = None
    y: Optional[int] = 5
    print(x == y, x == None, y == 5, x is y, x, y)
    z = y if y is not None and y > 3 else None
    w = None if x is None else x + 1
    print(z, w)
    a = Item("a")
    b = Item("b")
    c = Item("c")
    b.attach(a)
    c.attach(b)
    print(c.root().name, a.root().name, c.parent is b, a.parent is None, a.label())
    a.note = "hi"
    print(a.label(), c.note)
    names: dict[str, Optional[str]] = {"p": "x", "q": None}
    print(names, names.get("p"), names.get("q"), names.get("r"))
    try_val: Optional[str] = names["q"]
    print(try_val is None, try_val)
    print(bool(x), bool(y), not x)


if __name__ == "__main__":
    main()

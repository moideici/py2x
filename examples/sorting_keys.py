def by_second(p: tuple[str, int]) -> int:
    return p[1]


def main() -> None:
    words = ["pear", "fig", "apple", "kiwi", "banana", "plum", "date"]
    print(sorted(words), sorted(words, key=len), sorted(words, key=len, reverse=True), sorted(words, reverse=True))
    print(sorted(words, key=lambda w: (len(w), w)), sorted(words, key=lambda w: -len(w)))
    pairs = [("b", 2), ("a", 2), ("c", 1), ("d", 3), ("e", 1), ("f", 3)]
    print(sorted(pairs, key=lambda p: p[1]), sorted(pairs, key=lambda p: p[1], reverse=True))
    print(sorted(pairs, key=lambda p: (-p[1], p[0])), sorted(pairs, key=by_second))
    nums = [5, -3, 8, -1, 0, 7, 3, -5]
    print(sorted(nums, key=abs), sorted(nums, key=lambda n: n % 3), sorted(nums, reverse=True), sorted(nums, key=lambda n: n > 0))
    nums.sort(key=lambda n: -n)
    print(nums)
    mixed = ["b", "A", "c", "B", "a"]
    mixed.sort(key=str.lower)
    print(mixed)
    mixed.sort(key=lambda s: s.lower(), reverse=True)
    print(mixed)
    print(min(words, key=len), max(words, key=len), min(nums, key=abs), max(pairs, key=lambda p: p[1]), min(pairs, key=by_second))
    empty: list[str] = []
    print(max(empty, key=len, default="none"), min(nums, default=0), max(empty, default="x"))
    print(max(3, 9, 4, key=lambda v: -v), min("b", "a", "c"), max(1, 2, 3))
    a = b = c = 5
    a += 1
    print(a, b, c)
    x = y = [1]
    x.append(2)
    print(x, y)
    i = j = 0
    for k in range(3):
        i += k
        j -= k
    print(i, j)
    print(sorted("hello world"), sorted("banana", reverse=True), sorted([3, 1, 2]))


if __name__ == "__main__":
    main()

def main() -> None:
    s = "  Hello, World!  "
    print(s.strip() + "|", s.lstrip() + "|", s.rstrip() + "|")
    print(s.upper(), s.lower(), "hello world".title(), "hELLO".capitalize(), "Hello".swapcase())
    print("a,b,,c".split(","), "a  b   c".split(), "a,b,c,d".split(",", 2), "x\ny\r\nz".splitlines())
    print("-".join(["a", "b", "c"]), "".join(str(i) for i in range(5)), ", ".join([]))
    print("banana".replace("a", "o"), "banana".replace("an", "", 1), "abc".replace("", "-"))
    print("hello".startswith("he"), "hello".endswith("lo"), "hello".find("l"), "hello".rfind("l"), "hello".count("l"), "hello".find("z"))
    print("123".isdigit(), "abc".isalpha(), "ab1".isalnum(), "  ".isspace(), "abc".islower(), "ABC".isupper(), "".isdigit())
    print("42".zfill(5), "-42".zfill(6), "ab".ljust(5, "*") + "|", "ab".rjust(5) + "|", "ab".center(7, "-"), "abc".center(6) + "|")
    print("prefix_name".removeprefix("prefix_"), "name.py".removesuffix(".py"))
    print(ord("A"), chr(97), int("  42 "), int("-7"), float("3.5"), float("1e3"), int("1_000"))

    word = "Programming"
    print(word[0], word[-1], word[1:4], word[:3], word[3:], word[-3:], word[::2], word[::-1], word[8:2:-2], word[100:])
    nums = [10, 20, 30, 40, 50, 60]
    print(nums[1:3], nums[:2], nums[4:], nums[-2:], nums[::2], nums[::-1], nums[5:1:-2], nums[:])
    nums[1:3] = [1, 2, 3]
    print(nums)
    nums[::2] = [0, 0, 0, 0]
    print(nums)
    del nums[0]
    del nums[1:3]
    print(nums)
    for ch in "abc":
        print(ch, ord(ch))
    print([c.upper() for c in "hello"], sorted("banana"), list("xyz"), max("hello"), min("hello"))
    for i, c in enumerate("ab"):
        print(i, c)
    for a, b in zip("abc", [1, 2, 3]):
        print(a, b)

    x, n, name = 3.14159, 42, "pi"
    print(f"{x:.2f} {x:8.3f}|{x:<8.1f}|{x:^9.2f}|{-x:+.1f} {x:e} {x:g}")
    print(f"{n:5d}|{n:<5d}|{n:^5d}|{n:05d}|{n:+d}|{n:x}|{n:X}|{n:b}|{n:o}|{n:#x}|{n:#b}|{n:,}")
    print(f"{1234567:,} {1234567.891:,.2f} {0.5:.0%} {0.256:.1%} {1e-7:g} {123456789.0:g}")
    print(f"{name:>6}|{name:<6}|{name:^6}|{name:*^7}|{name:.1}|{name!r}|{n!r:>6}")
    print("{} and {}".format(1, "two"), "{0}-{1}-{0}".format("a", "b"), "{name}={val:.1f}".format(name="k", val=2.25))
    print("%d items, %s, %.2f%%, %5d|%-5s|%05d|%x" % (3, "ok", 99.5, 42, "ab", 7, 255))
    print("%s" % "single", "%d" % 5, "%5.1f" % 3.14159)

    print(round(2.5), round(3.5), round(-0.5), round(2.675, 2), round(1.5), round(0.1 + 0.2, 5), round(7))
    print(divmod(17, 5), divmod(-17, 5), pow(2, 10), pow(3, 4, 5), bin(10), hex(255), oct(8), bin(-5))
    print((37).bit_length(), (255).bit_count(), abs(-3.5), bool(0), bool("x"), repr("it's"), repr(3.0), repr([1, 2]), repr(["a", "b"]))
    print(1, 2, 3, sep=", ", end="!\n")
    print("no newline", end="")
    print()
    print("a", "b", sep="")
    nums2 = [1, 2, 3]
    print(sum(nums2, 10), sum([0.1, 0.2], 0.5), sum(x * 0.5 for x in nums2))
    for k in (1, 2, 3):
        print(k, k in (2, 3), k not in (4, 5))


if __name__ == "__main__":
    main()

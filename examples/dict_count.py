def count_words(words: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for w in words:
        if w in counts:
            counts[w] += 1
        else:
            counts[w] = 1
    return counts


def main() -> None:
    c: dict[str, int] = count_words(["a", "b", "a", "c", "b", "a"])
    print(c["a"], c["b"], c["c"], len(c))
    total: int = 0
    for k in c:
        total += c[k]
    print(total)
    print(c.get("z", -1), c.get("a", -1))
    print("b" in c, "q" in c)


if __name__ == "__main__":
    main()

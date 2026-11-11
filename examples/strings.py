def reverse(s: str) -> str:
    r: str = ""
    i: int = len(s) - 1
    while i >= 0:
        r += s[i]
        i -= 1
    return r


def is_pal(s: str) -> bool:
    return s == reverse(s)


def main() -> None:
    words: list[str] = ["level", "hello", "noon"]
    for w in words:
        print(w, reverse(w), is_pal(w))
    print(f"total={len(words)}")
    print(words)
    print("ell" in "hello", "z" in "hello")
    label: str = "pair" if len(words) % 2 == 0 else "impair"
    print(label)


if __name__ == "__main__":
    main()

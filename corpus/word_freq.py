import string

TEXT = """The quick brown fox jumps over the lazy dog. The dog barks;
the fox runs away! Quick, quick, said the fox."""


def tokenize(text: str) -> list[str]:
    cleaned = text.lower()
    for ch in string.punctuation:
        cleaned = cleaned.replace(ch, " ")
    return cleaned.split()


def count_words(words: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return counts


def main() -> None:
    words = tokenize(TEXT)
    counts = count_words(words)
    print(f"{len(words)} words, {len(counts)} distinct")
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for word, n in ranked[:5]:
        print(f"{word:<8} {n:>3} {'*' * n}")
    longest = max(words, key=len)
    print("longest:", longest, len(longest))


if __name__ == "__main__":
    main()

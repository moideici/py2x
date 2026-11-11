from collections import Counter, defaultdict

TEXT = """It was the best of times, it was the worst of times, it was the age of wisdom,
it was the age of foolishness, it was the epoch of belief, it was the epoch of incredulity,
it was the season of Light, it was the season of Darkness, it was the spring of hope,
it was the winter of despair."""


def tokenize(text: str) -> list[str]:
    words: list[str] = []
    current = ""
    for ch in text.lower():
        if ch.isalpha() or ch == "'":
            current += ch
        elif current:
            words.append(current)
            current = ""
    if current:
        words.append(current)
    return words


def sentences(text: str) -> list[str]:
    parts = [p.strip() for p in text.replace("\n", " ").split(".")]
    return [p for p in parts if p]


def bigrams(words: list[str]) -> Counter[tuple[str, str]]:
    return Counter(zip(words, words[1:]))


def index_by_length(words: list[str]) -> dict[int, list[str]]:
    groups: dict[int, list[str]] = defaultdict(list)
    for w in words:
        if w not in groups[len(w)]:
            groups[len(w)].append(w)
    return dict(groups)


def longest_common_prefix(words: list[str]) -> str:
    if not words:
        return ""
    prefix = words[0]
    for w in words[1:]:
        while not w.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix


def main() -> None:
    words = tokenize(TEXT)
    print(len(words), len(set(words)))
    freq = Counter(words)
    print(freq.most_common(5))
    print(sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[5:9])
    print(bigrams(words).most_common(3))
    idx = index_by_length(words)
    print(sorted(idx), idx[2], idx.get(10, []))
    print(longest_common_prefix(["season", "seas", "sea"]), repr(longest_common_prefix(["a", "b"])))
    sents = sentences(TEXT)
    print(len(sents), [len(s.split()) for s in sents])
    print(max(words, key=len), min(words, key=lambda w: (len(w), w)), sum(len(w) for w in words) / len(words))
    caps = [w for w in TEXT.split() if w[0].isupper()]
    print(caps, TEXT.count("it was"), TEXT.find("age"), TEXT.rfind("age"))


if __name__ == "__main__":
    main()

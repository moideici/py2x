from collections import defaultdict


def is_palindrome(s: str) -> bool:
    cleaned = "".join(ch.lower() for ch in s if ch.isalnum())
    return cleaned == cleaned[::-1]


def caesar(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if ch.isalpha():
            base = ord("a") if ch.islower() else ord("A")
            out.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            out.append(ch)
    return "".join(out)


def group_anagrams(words: list[str]) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for w in words:
        groups["".join(sorted(w))].append(w)
    return [g for _, g in sorted(groups.items())]


def title_case(sentence: str) -> str:
    return " ".join(w.capitalize() for w in sentence.split())


def vowel_count(s: str) -> int:
    return sum(1 for ch in s.lower() if ch in "aeiou")


def main() -> None:
    print(is_palindrome("A man, a plan, a canal: Panama"), is_palindrome("hello"))
    enc = caesar("Hello, World!", 3)
    print(enc, caesar(enc, -3))
    print(group_anagrams(["listen", "silent", "enlist", "google", "gogole", "cat", "act"]))
    print(title_case("the quick  brown fox"))
    print(vowel_count("Programming Language"), "abc".upper(), "  pad ".strip() + "|")
    print("a,b,,c".split(","), "x".join(["1", "2", "3"]), "hello".startswith("he"), "hello".find("l"))


if __name__ == "__main__":
    main()

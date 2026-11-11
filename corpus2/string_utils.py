import string


def caesar(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            out.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            out.append(ch)
    return "".join(out)


def rle_encode(s: str) -> str:
    if not s:
        return ""
    parts: list[str] = []
    count = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            count += 1
        else:
            parts.append(f"{count}{s[i - 1]}")
            count = 1
    parts.append(f"{count}{s[-1]}")
    return "".join(parts)


def rle_decode(s: str) -> str:
    out = ""
    num = ""
    for ch in s:
        if ch.isdigit():
            num += ch
        else:
            out += ch * int(num)
            num = ""
    return out


def is_palindrome(s: str) -> bool:
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]


def word_wrap(text: str, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = word if not current else current + " " + word
    if current:
        lines.append(current)
    return lines


def char_freq(s: str) -> dict[str, int]:
    freq: dict[str, int] = {}
    for ch in s.lower():
        if ch in string.ascii_lowercase:
            freq[ch] = freq.get(ch, 0) + 1
    return freq


def title(s: str) -> str:
    return " ".join(w[0].upper() + w[1:].lower() for w in s.split())


def main() -> None:
    msg = "Hello, World! xyz"
    enc = caesar(msg, 3)
    print(enc, caesar(enc, -3))
    r = rle_encode("aaabccddddd")
    print(r, rle_decode(r), rle_encode(""))
    print(is_palindrome("A man, a plan, a canal: Panama"), is_palindrome("hello"))
    for line in word_wrap("the quick brown fox jumps over the lazy dog again and again", 16):
        print(f"|{line:<16}|")
    f = char_freq("Mississippi River")
    print(sorted(f.items(), key=lambda kv: (-kv[1], kv[0]))[:4])
    print(title("hELLO wORLD of pYTHON"), "abc".center(9, "*"), "x".rjust(4, "0"), "42".zfill(6))
    print("a,b,,c".split(","), "  pad  ".strip(), "x-y-z".replace("-", "+"), "hello".find("l"), "hello".count("l"))


if __name__ == "__main__":
    main()

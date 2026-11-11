ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
SCALES = [(1_000_000_000, "billion"), (1_000_000, "million"), (1000, "thousand")]


def below_thousand(n: int) -> str:
    parts: list[str] = []
    if n >= 100:
        parts.append(ONES[n // 100] + " hundred")
        n %= 100
    if n >= 20:
        word = TENS[n // 10]
        if n % 10:
            word += "-" + ONES[n % 10]
        parts.append(word)
    elif n > 0 or not parts:
        parts.append(ONES[n])
    return " ".join(parts)


def to_words(n: int) -> str:
    if n < 0:
        return "minus " + to_words(-n)
    if n == 0:
        return "zero"
    parts: list[str] = []
    for value, name in SCALES:
        if n >= value:
            parts.append(below_thousand(n // value) + " " + name)
            n %= value
    if n > 0:
        parts.append(below_thousand(n))
    return " ".join(parts)


def to_roman(n: int) -> str:
    table = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"),
             (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for value, sym in table:
        while n >= value:
            out += sym
            n -= value
    return out


def from_roman(s: str) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        if i + 1 < len(s) and vals[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def main() -> None:
    for n in (0, 7, 13, 21, 100, 101, 342, 1000, 12345, 1000001, 2147483647, -45):
        print(n, "->", to_words(n))
    for n in (4, 9, 14, 40, 90, 400, 1994, 2024, 3999):
        r = to_roman(n)
        print(n, r, from_roman(r) == n)
    print([ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 101, 111)])


if __name__ == "__main__":
    main()

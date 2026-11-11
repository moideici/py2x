NUMERALS = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
            (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def to_roman(n: int) -> str:
    out = ""
    for value, sym in NUMERALS:
        while n >= value:
            out += sym
            n -= value
    return out


def from_roman(s: str) -> int:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for i, ch in enumerate(s):
        v = values[ch]
        if i + 1 < len(s) and values[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total


def is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def day_of_week(y: int, m: int, d: int) -> str:
    names = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    if m < 3:
        m += 12
        y -= 1
    k, j = y % 100, y // 100
    h = (d + 13 * (m + 1) // 5 + k + k // 4 + j // 4 + 5 * j) % 7
    return names[h]


def main() -> None:
    for n in (4, 9, 14, 40, 90, 400, 1994, 2024):
        r = to_roman(n)
        print(n, r, from_roman(r))
    print([y for y in range(1896, 1912) if is_leap(y)])
    print(day_of_week(2024, 2, 29), day_of_week(2000, 1, 1))


if __name__ == "__main__":
    main()

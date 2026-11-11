def add(a: str, b: str) -> str:
    i, j = len(a) - 1, len(b) - 1
    carry = 0
    out: list[str] = []
    while i >= 0 or j >= 0 or carry:
        s = carry
        if i >= 0:
            s += int(a[i])
            i -= 1
        if j >= 0:
            s += int(b[j])
            j -= 1
        out.append(str(s % 10))
        carry = s // 10
    return "".join(reversed(out))


def multiply(a: str, b: str) -> str:
    if a == "0" or b == "0":
        return "0"
    res = [0] * (len(a) + len(b))
    for i in range(len(a) - 1, -1, -1):
        for j in range(len(b) - 1, -1, -1):
            prod = int(a[i]) * int(b[j]) + res[i + j + 1]
            res[i + j + 1] = prod % 10
            res[i + j] += prod // 10
    s = "".join(str(d) for d in res)
    return s.lstrip("0")


def factorial(n: int) -> str:
    result = "1"
    for k in range(2, n + 1):
        result = multiply(result, str(k))
    return result


def power(base: int, exp: int) -> str:
    result = "1"
    b = str(base)
    while exp > 0:
        if exp % 2 == 1:
            result = multiply(result, b)
        b = multiply(b, b)
        exp //= 2
    return result


def digit_sum(s: str) -> int:
    return sum(int(c) for c in s)


def to_base(n: int, base: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    out = ""
    neg = n < 0
    n = abs(n)
    while n:
        out = digits[n % base] + out
        n //= base
    return "-" + out if neg else out


def main() -> None:
    print(add("99999999999999999999", "1"), add("123", "98765"))
    print(multiply("123456789", "987654321"))
    f = factorial(30)
    print(f, len(f), digit_sum(f))
    print(power(2, 100), digit_sum(power(7, 50)))
    print(to_base(255, 2), to_base(255, 16), to_base(-1000, 7), to_base(0, 3), int("ff", 16), int("-101", 2))
    print(bin(10), hex(255), oct(64), format(255, "08b"), format(3735928559, "X"))


if __name__ == "__main__":
    main()

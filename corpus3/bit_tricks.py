def popcount(n: int) -> int:
    count = 0
    while n:
        n &= n - 1
        count += 1
    return count


def reverse_bits(n: int, width: int) -> int:
    result = 0
    for _ in range(width):
        result = (result << 1) | (n & 1)
        n >>= 1
    return result


def gray(n: int) -> int:
    return n ^ (n >> 1)


def subsets(items: list[str]) -> list[list[str]]:
    out: list[list[str]] = []
    for mask in range(1 << len(items)):
        out.append([items[i] for i in range(len(items)) if mask >> i & 1])
    return out


def is_power_of_two(n: int) -> bool:
    return n > 0 and n & (n - 1) == 0


def to_binary(n: int, width: int = 8) -> str:
    return "".join("1" if n >> i & 1 else "0" for i in range(width - 1, -1, -1))


def xor_cipher(text: str, key: int) -> list[int]:
    return [ord(c) ^ key for c in text]


def hamming(a: int, b: int) -> int:
    return popcount(a ^ b)


def main() -> None:
    print([popcount(n) for n in (0, 1, 7, 255, 1023)], popcount(2 ** 40 - 1))
    print([reverse_bits(n, 8) for n in (1, 6, 128, 255)], [gray(n) for n in range(8)])
    print(subsets(["a", "b", "c"]))
    print([is_power_of_two(n) for n in (0, 1, 2, 3, 64, 100)], to_binary(37), to_binary(5, 4), hamming(0b1011, 0b0110))
    enc = xor_cipher("Hello", 42)
    print(enc, "".join(chr(c ^ 42) for c in enc))
    flags = 0
    for bit in (0, 3, 5):
        flags |= 1 << bit
    flags &= ~(1 << 3)
    print(flags, bin(flags), hex(flags << 4), flags.bit_length(), -17 >> 2, -17 & 0xFF, ~5, 5 ^ 3, 1 << 62)


if __name__ == "__main__":
    main()

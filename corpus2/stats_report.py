import math
from collections import Counter


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2


def variance(xs: list[float]) -> float:
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def mode(xs: list[int]) -> list[int]:
    counts = Counter(xs)
    top = max(counts.values())
    return sorted(k for k, v in counts.items() if v == top)


def percentile(xs: list[float], p: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * p / 100
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return s[int(k)]
    return s[lo] * (hi - k) + s[hi] * (k - lo)


def histogram(xs: list[int], bins: int) -> list[int]:
    lo, hi = min(xs), max(xs)
    width = (hi - lo) / bins
    counts = [0] * bins
    for x in xs:
        i = min(int((x - lo) / width), bins - 1)
        counts[i] += 1
    return counts


def correlation(xs: list[float], ys: list[float]) -> float:
    mx, my = mean(xs), mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return cov / (sx * sy)


def main() -> None:
    data = [2.5, 3.5, 1.0, 4.0, 4.0, 9.5, 7.25, 3.0]
    print(f"mean={mean(data):.3f} median={median(data)} var={variance(data):.4f} sd={math.sqrt(variance(data)):.4f}")
    print(percentile(data, 25), percentile(data, 90), percentile(data, 100))
    ints = [3, 1, 3, 2, 2, 5, 3, 2]
    print(mode(ints), Counter(ints).most_common(2))
    print(histogram([1, 2, 2, 3, 3, 3, 8, 9, 10, 10], 3))
    print(round(correlation([1.0, 2.0, 3.0, 4.0], [2.1, 3.9, 6.2, 7.8]), 4))
    print(f"{math.pi:10.5f}|{math.e:<10.3e}|{1234567.891:,.1f}|{0.5:.0%}")
    print(min(data), max(data), sum(data), len(data), round(sum(data) / len(data), 2))


if __name__ == "__main__":
    main()

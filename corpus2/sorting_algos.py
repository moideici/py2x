class LCG:
    def __init__(self, seed: int) -> None:
        self.state = seed

    def next(self) -> int:
        self.state = (self.state * 1103515245 + 12345) % 2147483648
        return self.state

    def below(self, n: int) -> int:
        return self.next() % n


def merge_sort(xs: list[int]) -> list[int]:
    if len(xs) <= 1:
        return xs
    mid = len(xs) // 2
    left, right = merge_sort(xs[:mid]), merge_sort(xs[mid:])
    out: list[int] = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out


def quick_sort(xs: list[int], lo: int, hi: int) -> None:
    if lo >= hi:
        return
    pivot = xs[(lo + hi) // 2]
    i, j = lo, hi
    while i <= j:
        while xs[i] < pivot:
            i += 1
        while xs[j] > pivot:
            j -= 1
        if i <= j:
            xs[i], xs[j] = xs[j], xs[i]
            i += 1
            j -= 1
    quick_sort(xs, lo, j)
    quick_sort(xs, i, hi)


def heap_sort(xs: list[int]) -> None:
    n = len(xs)

    def sift(root: int, end: int) -> None:
        while True:
            child = 2 * root + 1
            if child >= end:
                return
            if child + 1 < end and xs[child] < xs[child + 1]:
                child += 1
            if xs[root] >= xs[child]:
                return
            xs[root], xs[child] = xs[child], xs[root]
            root = child

    for start in range(n // 2 - 1, -1, -1):
        sift(start, n)
    for end in range(n - 1, 0, -1):
        xs[0], xs[end] = xs[end], xs[0]
        sift(0, end)


def insertion_sort(xs: list[int]) -> int:
    shifts = 0
    for i in range(1, len(xs)):
        key = xs[i]
        j = i - 1
        while j >= 0 and xs[j] > key:
            xs[j + 1] = xs[j]
            j -= 1
            shifts += 1
        xs[j + 1] = key
    return shifts


def bsearch(xs: list[int], target: int) -> int:
    lo, hi = 0, len(xs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if xs[mid] == target:
            return mid
        if xs[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -(lo + 1)


def main() -> None:
    rng = LCG(42)
    data = [rng.below(100) for _ in range(20)]
    print(data)
    a = merge_sort(data)
    b = data[:]
    quick_sort(b, 0, len(b) - 1)
    c = data[:]
    heap_sort(c)
    d = data[:]
    shifts = insertion_sort(d)
    print(a)
    print(a == b == c == d == sorted(data), shifts)
    print(bsearch(a, a[7]), bsearch(a, 1000), bsearch(a, -5), bsearch([], 3))


if __name__ == "__main__":
    main()

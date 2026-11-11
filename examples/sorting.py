def bubble(xs: list[int]) -> None:
    n: int = len(xs)
    for i in range(n):
        for j in range(n - 1 - i):
            if xs[j] > xs[j + 1]:
                xs[j], xs[j + 1] = xs[j + 1], xs[j]


def bsearch(xs: list[int], t: int) -> int:
    lo: int = 0
    hi: int = len(xs) - 1
    while lo <= hi:
        mid: int = (lo + hi) // 2
        if xs[mid] == t:
            return mid
        elif xs[mid] < t:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def main() -> None:
    data: list[int] = [5, 2, 9, 1, 7, 3]
    bubble(data)
    print(data, bsearch(data, 9), bsearch(data, 4))
    print(data[-1], data[0], sorted([3, 1, 2]))
    data.reverse()
    print(data)
    names: list[str] = ["pear", "apple", "fig"]
    names.sort()
    print(names)
    grid: list[list[int]] = [[1, 2], [3, 4]]
    grid[1][0] = 30
    print(grid, len(grid))


if __name__ == "__main__":
    main()

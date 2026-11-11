def lcs(a: str, b: str) -> str:
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            if a[i] == b[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(dp[i][j + 1], dp[i + 1][j])
    out: list[str] = []
    i, j = n, m
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            out.append(a[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return "".join(reversed(out))


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[-1]


def coin_change(coins: list[int], amount: int) -> int:
    INF = amount + 1
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return dp[amount] if dp[amount] != INF else -1


def lis(nums: list[int]) -> list[int]:
    if not nums:
        return []
    tails: list[int] = []
    idx: list[int] = []
    prev = [-1] * len(nums)
    for i, x in enumerate(nums):
        lo, hi = 0, len(tails)
        while lo < hi:
            mid = (lo + hi) // 2
            if nums[tails[mid]] < x:
                lo = mid + 1
            else:
                hi = mid
        if lo > 0:
            prev[i] = tails[lo - 1]
        if lo == len(tails):
            tails.append(i)
        else:
            tails[lo] = i
    k = tails[-1]
    out: list[int] = []
    while k != -1:
        out.append(nums[k])
        k = prev[k]
    return out[::-1]


def count_paths(grid: list[str]) -> int:
    rows, cols = len(grid), len(grid[0])
    ways = [[0] * cols for _ in range(rows)]
    ways[0][0] = 1 if grid[0][0] == "." else 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "#":
                ways[r][c] = 0
                continue
            if r > 0:
                ways[r][c] += ways[r - 1][c]
            if c > 0:
                ways[r][c] += ways[r][c - 1]
    return ways[-1][-1]


def fib_memo(n: int, memo: dict[int, int]) -> int:
    if n < 2:
        return n
    if n in memo:
        return memo[n]
    memo[n] = fib_memo(n - 1, memo) + fib_memo(n - 2, memo)
    return memo[n]


def main() -> None:
    print(lcs("AGGTAB", "GXTXAYB"), edit_distance("kitten", "sitting"), edit_distance("", "abc"))
    print(coin_change([1, 5, 10, 25], 63), coin_change([2], 3))
    print(lis([10, 9, 2, 5, 3, 7, 101, 18]), lis([]))
    print(count_paths(["...", ".#.", "..."]), count_paths(["..#", "###", "..."]))
    memo: dict[int, int] = {}
    print(fib_memo(80, memo), len(memo))


if __name__ == "__main__":
    main()

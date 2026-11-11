def knapsack(weights: list[int], values: list[int], capacity: int) -> tuple[int, list[int]]:
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            dp[i][w] = dp[i - 1][w]
            if weights[i - 1] <= w:
                dp[i][w] = max(dp[i][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
    chosen: list[int] = []
    w = capacity
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            chosen.append(i - 1)
            w -= weights[i - 1]
    chosen.reverse()
    return dp[n][capacity], chosen


def lcs(a: str, b: str) -> str:
    m, n = len(a), len(b)
    table = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m):
        for j in range(n):
            if a[i] == b[j]:
                table[i + 1][j + 1] = table[i][j] + 1
            else:
                table[i + 1][j + 1] = max(table[i][j + 1], table[i + 1][j])
    out = []
    i, j = m, n
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            out.append(a[i - 1])
            i -= 1
            j -= 1
        elif table[i - 1][j] >= table[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return "".join(reversed(out))


def main() -> None:
    best, items = knapsack([12, 2, 1, 1, 4], [4, 2, 1, 2, 10], 15)
    print(best, items)
    print(lcs("AGGTAB", "GXTXAYB"))


if __name__ == "__main__":
    main()

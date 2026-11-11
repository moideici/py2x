Grid = list[list[int]]


def neighbors(grid: Grid, r: int, c: int) -> int:
    rows, cols = len(grid), len(grid[0])
    total = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < rows and 0 <= cc < cols:
                total += grid[rr][cc]
    return total


def step(grid: Grid) -> Grid:
    new = [[0] * len(grid[0]) for _ in grid]
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            n = neighbors(grid, r, c)
            if grid[r][c] == 1 and n in (2, 3):
                new[r][c] = 1
            elif grid[r][c] == 0 and n == 3:
                new[r][c] = 1
    return new


def render(grid: Grid) -> str:
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)


def main() -> None:
    grid = [
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    for gen in range(3):
        print(f"gen {gen}")
        print(render(grid))
        grid = step(grid)
    print("alive:", sum(sum(row) for row in grid))


if __name__ == "__main__":
    main()

from typing import Optional

LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def winner(board: list[str]) -> Optional[str]:
    for a, b, c in LINES:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]
    return None


def moves(board: list[str]) -> list[int]:
    return [i for i, cell in enumerate(board) if cell == " "]


def minimax(board: list[str], player: str, counter: list[int]) -> int:
    counter[0] += 1
    w = winner(board)
    if w == "X":
        return 1
    if w == "O":
        return -1
    free = moves(board)
    if not free:
        return 0
    scores: list[int] = []
    for m in free:
        board[m] = player
        scores.append(minimax(board, "O" if player == "X" else "X", counter))
        board[m] = " "
    return max(scores) if player == "X" else min(scores)


def best_move(board: list[str], player: str) -> int:
    best = -1
    best_score = -2 if player == "X" else 2
    counter = [0]
    for m in moves(board):
        board[m] = player
        score = minimax(board, "O" if player == "X" else "X", counter)
        board[m] = " "
        if (player == "X" and score > best_score) or (player == "O" and score < best_score):
            best_score = score
            best = m
    return best


def render(board: list[str]) -> str:
    rows = ["|".join(board[i:i + 3]) for i in range(0, 9, 3)]
    return "\n-+-+-\n".join(rows)


def play() -> None:
    board = [" "] * 9
    player = "X"
    board[0] = "X"
    player = "O"
    while moves(board) and winner(board) is None:
        m = best_move(board, player)
        board[m] = player
        player = "O" if player == "X" else "X"
    print(render(board))
    print("winner:", winner(board))


def main() -> None:
    b = list("XX OO    ")
    print(best_move(b, "X"), best_move(b, "O"))
    c = [0]
    print(minimax(list("         "), "X", c), c[0])
    play()


if __name__ == "__main__":
    main()

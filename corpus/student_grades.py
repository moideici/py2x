def average(xs: list[int]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def letter(avg: float) -> str:
    if avg >= 90:
        return "A"
    if avg >= 80:
        return "B"
    if avg >= 70:
        return "C"
    return "F"


def main() -> None:
    grades = {
        "alice": [92, 88, 95],
        "bob": [75, 64, 80, 71],
        "carol": [100, 97],
        "dave": [],
    }
    for name in sorted(grades):
        avg = average(grades[name])
        print(f"{name:<6} {avg:6.2f} {letter(avg)}")
    best = max(grades, key=lambda n: average(grades[n]))
    print("best:", best, round(average(grades[best]), 1))
    all_scores = [s for scores in grades.values() for s in scores]
    print(len(all_scores), min(all_scores), max(all_scores), round(average(all_scores), 3))
    passed = {n: average(s) for n, s in grades.items() if average(s) >= 70}
    print(passed)


if __name__ == "__main__":
    main()

"""rsplit: limites, chevauchement, blancs ASCII et erreurs."""

def main() -> None:
    texts: list[str] = ["", "a", "aaaaa", "ababa", "::a::::b::", " a  b c  ", "\t a\n b\r\v", "   "]
    separators: list[str] = ["a", "aa", "aba", "::", " ", "missing"]
    limits: list[int] = [-2, -1, 0, 1, 2, 9, 9223372036854775807]
    for text in texts:
        for separator in separators:
            for limit in limits:
                print(text.rsplit(separator, limit))
            print(text.rsplit(separator))
        for limit in limits:
            print(text.rsplit(None, limit))
        print(text.rsplit(), text.rsplit(None))
    try:
        print("".rsplit("", 0))
    except ValueError as error:
        print(error)

if __name__ == "__main__":
    main()

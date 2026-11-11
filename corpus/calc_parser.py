class Parser:
    def __init__(self, text: str) -> None:
        self.tokens = self.tokenize(text)
        self.pos = 0

    @staticmethod
    def tokenize(text: str) -> list[str]:
        tokens: list[str] = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch.isspace():
                i += 1
            elif ch.isdigit():
                j = i
                while j < len(text) and text[j].isdigit():
                    j += 1
                tokens.append(text[i:j])
                i = j
            elif ch in "+-*/()":
                tokens.append(ch)
                i += 1
            else:
                raise ValueError(f"bad character {ch!r}")
        return tokens

    def peek(self) -> str:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ""

    def advance(self) -> str:
        tok = self.peek()
        self.pos += 1
        return tok

    def expr(self) -> int:
        value = self.term()
        while self.peek() in ("+", "-"):
            op = self.advance()
            rhs = self.term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def term(self) -> int:
        value = self.factor()
        while self.peek() in ("*", "/"):
            op = self.advance()
            rhs = self.factor()
            if op == "*":
                value *= rhs
            else:
                value //= rhs
        return value

    def factor(self) -> int:
        tok = self.advance()
        if tok == "(":
            value = self.expr()
            self.advance()
            return value
        if tok == "-":
            return -self.factor()
        return int(tok)


def evaluate(text: str) -> int:
    return Parser(text).expr()


def main() -> None:
    for src in ["1 + 2 * 3", "(1 + 2) * 3", "10 / 3 - 1", "-(4 + 5) * 2", "2 * (3 + (4 - 1))"]:
        print(f"{src} = {evaluate(src)}")
    try:
        evaluate("2 $ 3")
    except ValueError as e:
        print("error:", e)


if __name__ == "__main__":
    main()

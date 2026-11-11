class InsufficientFunds(Exception):
    def __init__(self, needed: int, available: int) -> None:
        super().__init__(f"need {needed}, have {available}")
        self.needed = needed
        self.available = available


class Account:
    def __init__(self, owner: str, balance: int = 0) -> None:
        self.owner = owner
        self.balance = balance
        self.log: list[str] = []

    def deposit(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self.balance += amount
        self.log.append(f"deposit {amount}")

    def withdraw(self, amount: int) -> None:
        if amount > self.balance:
            raise InsufficientFunds(amount, self.balance)
        self.balance -= amount
        self.log.append(f"withdraw {amount}")

    def __str__(self) -> str:
        return f"{self.owner}: {self.balance}"


def transfer(src: Account, dst: Account, amount: int) -> bool:
    try:
        src.withdraw(amount)
    except InsufficientFunds as e:
        print("transfer failed:", e)
        return False
    dst.deposit(amount)
    return True


def main() -> None:
    a = Account("alice", 100)
    b = Account("bob")
    print(transfer(a, b, 30))
    print(transfer(a, b, 500))
    try:
        a.deposit(-5)
    except ValueError as e:
        print("error:", e)
    print(a, b)
    print(a.log, b.log)


if __name__ == "__main__":
    main()

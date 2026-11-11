from dataclasses import dataclass


@dataclass
class Item:
    name: str
    price: float
    qty: int = 1

    def total(self) -> float:
        return self.price * self.qty


def total_value(items: list[Item]) -> float:
    return sum(i.total() for i in items)


def cheapest(items: list[Item]) -> Item:
    return min(items, key=lambda i: i.price)


def main() -> None:
    items = [
        Item("pen", 1.5, 10),
        Item("notebook", 4.25, 3),
        Item("bag", 39.9),
        Item("ruler", 0.99, 5),
    ]
    for it in sorted(items, key=lambda i: i.total(), reverse=True):
        print(f"{it.name:<10} {it.qty:>3} x {it.price:>6.2f} = {it.total():>7.2f}")
    print(f"total: {total_value(items):.2f}")
    print("cheapest:", cheapest(items).name)
    expensive = [i.name for i in items if i.price > 2]
    print(", ".join(expensive))


if __name__ == "__main__":
    main()

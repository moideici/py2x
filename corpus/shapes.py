import math


class Shape:
    def __init__(self, name: str) -> None:
        self.name = name

    def area(self) -> float:
        return 0.0

    def describe(self) -> str:
        return f"{self.name} with area {self.area():.2f}"


class Circle(Shape):
    def __init__(self, radius: float) -> None:
        super().__init__("circle")
        self.radius = radius

    def area(self) -> float:
        return math.pi * self.radius ** 2


class Rect(Shape):
    def __init__(self, w: float, h: float) -> None:
        super().__init__("rect")
        self.w = w
        self.h = h

    def area(self) -> float:
        return self.w * self.h


class Square(Rect):
    def __init__(self, side: float) -> None:
        super().__init__(side, side)
        self.name = "square"


def main() -> None:
    shapes: list[Shape] = [Circle(1.5), Rect(2.0, 3.0), Square(4.0)]
    for s in shapes:
        print(s.describe())
    total = sum(s.area() for s in shapes)
    print(f"total area: {total:.3f}")
    biggest = max(shapes, key=lambda s: s.area())
    print(biggest.name, isinstance(biggest, Rect))


if __name__ == "__main__":
    main()

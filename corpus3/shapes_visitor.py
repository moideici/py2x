import math
from abc import ABC, abstractmethod
from typing import Optional


class Shape(ABC):
    count = 0

    def __init__(self, name: str) -> None:
        self.name = name
        Shape.count += 1

    @abstractmethod
    def area(self) -> float:
        ...

    @abstractmethod
    def perimeter(self) -> float:
        ...

    def describe(self) -> str:
        return f"{self.name}: area={self.area():.2f} perimeter={self.perimeter():.2f}"

    def scale(self, k: float) -> "Shape":
        raise NotImplementedError("scale not implemented for " + self.name)


class Circle(Shape):
    def __init__(self, r: float) -> None:
        super().__init__("circle")
        self.r = r

    def area(self) -> float:
        return math.pi * self.r ** 2

    def perimeter(self) -> float:
        return 2 * math.pi * self.r

    def scale(self, k: float) -> "Shape":
        return Circle(self.r * k)


class Rectangle(Shape):
    def __init__(self, w: float, h: float, name: str = "rectangle") -> None:
        super().__init__(name)
        self.w = w
        self.h = h

    def area(self) -> float:
        return self.w * self.h

    def perimeter(self) -> float:
        return 2 * (self.w + self.h)

    def scale(self, k: float) -> "Shape":
        return Rectangle(self.w * k, self.h * k, self.name)


class Square(Rectangle):
    def __init__(self, side: float) -> None:
        super().__init__(side, side, "square")


class Triangle(Shape):
    def __init__(self, a: float, b: float, c: float) -> None:
        super().__init__("triangle")
        if a + b <= c or a + c <= b or b + c <= a:
            raise ValueError(f"invalid triangle sides {a}, {b}, {c}")
        self.a, self.b, self.c = a, b, c

    def area(self) -> float:
        s = self.perimeter() / 2
        return math.sqrt(s * (s - self.a) * (s - self.b) * (s - self.c))

    def perimeter(self) -> float:
        return self.a + self.b + self.c


def largest(shapes: list[Shape]) -> Optional[Shape]:
    best: Optional[Shape] = None
    for s in shapes:
        if best is None or s.area() > best.area():
            best = s
    return best


def total_area(shapes: list[Shape]) -> float:
    return sum(s.area() for s in shapes)


def main() -> None:
    shapes: list[Shape] = [Circle(1.0), Rectangle(2.0, 3.5), Square(2.5), Triangle(3.0, 4.0, 5.0)]
    for s in shapes:
        print(s.describe())
    print(f"{total_area(shapes):.3f}", Shape.count)
    big = largest(shapes)
    print(big.name if big is not None else "none", largest([]) is None)
    for s in shapes:
        try:
            t = s.scale(2.0)
            print(t.name, round(t.area() / s.area(), 6))
        except NotImplementedError as e:
            print("cannot scale:", e)
    try:
        Triangle(1.0, 2.0, 10.0)
    except ValueError as e:
        print(e)
    kinds = sorted(s.name for s in shapes)
    print(kinds, sum(1 for s in shapes if isinstance(s, Rectangle)), Shape.count)
    ordered = sorted(shapes, key=lambda s: (s.area(), s.name))
    print([s.name for s in ordered])


if __name__ == "__main__":
    main()

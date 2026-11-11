from abc import ABC, abstractmethod
from typing import Optional


class AppError(Exception):
    pass


class ParseError(AppError):
    def __init__(self, text: str, pos: int) -> None:
        super().__init__(f"bad token {text!r} at {pos}")
        self.text = text
        self.pos = pos


class LimitError(AppError):
    def __init__(self, limit: int) -> None:
        self.limit = limit


class Animal(ABC):
    def __init__(self, name: str, legs: int) -> None:
        self.name = name
        self.legs = legs
        self.energy = 10

    @abstractmethod
    def sound(self) -> str:
        return "..."

    def speak(self) -> str:
        return f"{self.name} says {self.sound()}"

    def tire(self, n: int) -> None:
        self.energy -= n

    def __str__(self) -> str:
        return f"{self.name}({self.legs} legs, energy {self.energy})"


class Dog(Animal):
    def __init__(self, name: str) -> None:
        super().__init__(name, 4)
        self.tricks: list[str] = []

    def sound(self) -> str:
        return "woof"

    def learn(self, trick: str) -> None:
        self.tricks.append(trick)

    def tire(self, n: int) -> None:
        super().tire(n * 2)


class Puppy(Dog):
    def sound(self) -> str:
        return "yip"

    def speak(self) -> str:
        return super().speak() + "!"


class Bird(Animal):
    def __init__(self, name: str, can_fly: bool) -> None:
        super().__init__(name, 2)
        self.can_fly = can_fly

    def sound(self) -> str:
        return "tweet"


def parse(tokens: list[str]) -> int:
    total = 0
    for i, t in enumerate(tokens):
        try:
            total += int(t)
        except ValueError:
            raise ParseError(t, i)
    return total


def risky(n: int) -> int:
    log: list[str] = []
    try:
        log.append("start")
        if n == 0:
            raise LimitError(0)
        if n < 0:
            raise ValueError("negative")
        r = 100 // (n - 1)
        log.append(f"r={r}")
        return r
    except ZeroDivisionError as e:
        log.append(f"zde:{e}")
        return -1
    except LimitError as e:
        log.append(f"limit:{e.limit}:{e}")
        raise
    except (ValueError, KeyError) as e:
        log.append(f"vk:{e}")
        return -2
    else:
        log.append("else")
    finally:
        log.append("finally")
        print(log)
    return 0


def describe(a: Animal) -> str:
    if isinstance(a, Puppy):
        return "puppy " + a.name + " tricks=" + str(len(a.tricks))
    if isinstance(a, Dog):
        return "dog with " + str(len(a.tricks)) + " tricks"
    if isinstance(a, Bird):
        return "bird flying=" + str(a.can_fly)
    return "animal"


def lookup(d: dict[str, int], xs: list[int], i: int, key: str) -> int:
    try:
        return xs[i] + d[key]
    except IndexError as e:
        print("index:", e)
    except KeyError as e:
        print("key:", e)
    return 0


def main() -> None:
    print(parse(["1", "2", "3"]))
    try:
        parse(["4", "x5", "6"])
    except ParseError as e:
        print("parse error:", e, e.text, e.pos)
    except AppError:
        print("other app error")
    for n in (3, 1, 0, -4):
        try:
            print("risky ->", risky(n))
        except AppError as e:
            print("caught", type(e).__name__, e)
    zoo: list[Animal] = [Dog("rex"), Puppy("bit"), Bird("tweety", True)]
    for a in zoo:
        a.tire(3)
        print(a.speak(), "|", a, "|", describe(a))
    d = Dog("fido")
    d.learn("sit")
    d.learn("roll")
    print(describe(d), d.tricks, d.energy)
    p = Puppy("pip")
    p.learn("beg")
    print(describe(p), p.speak())
    print(lookup({"a": 1}, [10, 20], 1, "a"), lookup({"a": 1}, [10, 20], 5, "a"), lookup({"a": 1}, [10, 20], 0, "b"))
    try:
        assert 1 + 1 == 3, "math is broken"
    except AssertionError as e:
        print("assert:", e)
    try:
        x: list[int] = []
        print(x[0])
    except Exception as e:
        print("generic:", e, repr(e))
    try:
        try:
            raise AppError("inner")
        finally:
            print("cleanup")
    except AppError as e:
        print("outer got", e)
    count = 0
    for i in range(6):
        try:
            if i % 2 == 0:
                continue
            if i == 5:
                break
            count += i
        finally:
            count += 100
    print(count)
    o: Optional[Animal] = Bird("o", False)
    if o is not None and isinstance(o, Bird):
        print(o.can_fly)
    print(isinstance(d, Animal), isinstance(d, Bird), isinstance(p, Dog))


if __name__ == "__main__":
    main()

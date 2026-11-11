from collections import OrderedDict
from typing import Optional


class LRUCache:
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self.data: OrderedDict[int, str] = OrderedDict()

    def get(self, key: int) -> Optional[str]:
        if key not in self.data:
            return None
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key: int, value: str) -> None:
        if key in self.data:
            self.data.move_to_end(key)
        self.data[key] = value
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)


class Stack:
    def __init__(self) -> None:
        self.items: list[int] = []

    def push(self, x: int) -> None:
        self.items.append(x)

    def pop(self) -> int:
        if not self.items:
            raise IndexError("pop from empty stack")
        return self.items.pop()

    def __len__(self) -> int:
        return len(self.items)


def balanced(s: str) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack


def main() -> None:
    cache = LRUCache(2)
    cache.put(1, "one")
    cache.put(2, "two")
    print(cache.get(1))
    cache.put(3, "three")
    print(cache.get(2), cache.get(3), list(cache.data.keys()))
    st = Stack()
    for i in range(3):
        st.push(i * i)
    print(st.pop(), len(st))
    print(balanced("{[()]}"), balanced("([)]"), balanced("(("))


if __name__ == "__main__":
    main()

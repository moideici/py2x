from typing import Optional


class Node:
    def __init__(self, value: int, next: Optional["Node"] = None) -> None:
        self.value = value
        self.next = next


class LinkedList:
    def __init__(self) -> None:
        self.head: Optional[Node] = None
        self.size = 0

    def push_front(self, value: int) -> None:
        self.head = Node(value, self.head)
        self.size += 1

    def push_back(self, value: int) -> None:
        node = Node(value)
        if self.head is None:
            self.head = node
        else:
            cur = self.head
            while cur.next is not None:
                cur = cur.next
            cur.next = node
        self.size += 1

    def reverse(self) -> None:
        prev: Optional[Node] = None
        cur = self.head
        while cur is not None:
            nxt = cur.next
            cur.next = prev
            prev = cur
            cur = nxt
        self.head = prev

    def to_list(self) -> list[int]:
        out = []
        cur = self.head
        while cur:
            out.append(cur.value)
            cur = cur.next
        return out


def main() -> None:
    ll = LinkedList()
    for v in [3, 2, 1]:
        ll.push_front(v)
    ll.push_back(4)
    print(ll.to_list(), ll.size)
    ll.reverse()
    print(ll.to_list())


if __name__ == "__main__":
    main()

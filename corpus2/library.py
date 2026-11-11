from dataclasses import dataclass
from typing import Optional


@dataclass
class Book:
    isbn: str
    title: str
    author: str
    year: int
    copies: int = 1


class Member:
    def __init__(self, name: str, limit: int = 2) -> None:
        self.name = name
        self.limit = limit
        self.borrowed: list[str] = []
        self.fines = 0.0

    def can_borrow(self) -> bool:
        return len(self.borrowed) < self.limit and self.fines < 10.0


class LibraryError(Exception):
    pass


class Library:
    def __init__(self) -> None:
        self.books: dict[str, Book] = {}
        self.members: dict[str, Member] = {}
        self.history: list[tuple[str, str, str]] = []

    def add_book(self, book: Book) -> None:
        if book.isbn in self.books:
            self.books[book.isbn].copies += book.copies
        else:
            self.books[book.isbn] = book

    def join(self, name: str) -> Member:
        m = Member(name)
        self.members[name] = m
        return m

    def find_by_author(self, author: str) -> list[Book]:
        return sorted((b for b in self.books.values() if b.author == author), key=lambda b: b.year)

    def checkout(self, member: str, isbn: str) -> None:
        m = self.members.get(member)
        if m is None:
            raise LibraryError(f"no such member: {member}")
        book = self.books.get(isbn)
        if book is None:
            raise LibraryError(f"no such book: {isbn}")
        if book.copies == 0:
            raise LibraryError(f"no copies left of {book.title!r}")
        if not m.can_borrow():
            raise LibraryError(f"{member} cannot borrow more")
        book.copies -= 1
        m.borrowed.append(isbn)
        self.history.append(("out", member, isbn))

    def give_back(self, member: str, isbn: str, days_late: int = 0) -> Optional[float]:
        m = self.members[member]
        if isbn not in m.borrowed:
            return None
        m.borrowed.remove(isbn)
        self.books[isbn].copies += 1
        fine = days_late * 0.5
        m.fines += fine
        self.history.append(("in", member, isbn))
        return fine


def main() -> None:
    lib = Library()
    lib.add_book(Book("111", "Dune", "Herbert", 1965))
    lib.add_book(Book("222", "Emma", "Austen", 1815, 2))
    lib.add_book(Book("333", "Persuasion", "Austen", 1817))
    lib.add_book(Book("111", "Dune", "Herbert", 1965))
    ann = lib.join("ann")
    lib.join("bob")
    print([b.title for b in lib.find_by_author("Austen")], lib.books["111"].copies)
    attempts = [("ann", "111"), ("ann", "222"), ("ann", "333"), ("bob", "999"), ("cy", "111"), ("bob", "333"), ("bob", "333")]
    for who, isbn in attempts:
        try:
            lib.checkout(who, isbn)
            print("ok", who, isbn)
        except LibraryError as e:
            print("fail:", e)
    print(lib.give_back("ann", "111", 5), lib.give_back("ann", "111"), ann.fines, ann.can_borrow())
    print(lib.history)
    print(lib.books["222"])


if __name__ == "__main__":
    main()

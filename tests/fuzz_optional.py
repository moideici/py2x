"""Fuzzer différentiel : None/Optional via une liste chaînée et un arbre binaire de recherche (insertion, suppression, parcours).

  python tests/fuzz_optional.py --target cpp --seeds 20
  python tests/fuzz_optional.py --target kotlin --seeds 3
"""
import argparse
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from py2x import Unsupported, transpile  # noqa: E402
from py2x.verify import build_and_run, python_output  # noqa: E402

HEADER = '''from typing import Optional


class Node:
    def __init__(self, val: int) -> None:
        self.val = val
        self.next = None


class LinkedList:
    def __init__(self) -> None:
        self.head = None
        self.size = 0

    def push_front(self, v: int) -> None:
        n = Node(v)
        n.next = self.head
        self.head = n
        self.size += 1

    def push_back(self, v: int) -> None:
        n = Node(v)
        if self.head is None:
            self.head = n
        else:
            cur = self.head
            while cur.next is not None:
                cur = cur.next
            cur.next = n
        self.size += 1

    def pop_front(self) -> Optional[int]:
        if self.head is None:
            return None
        v = self.head.val
        self.head = self.head.next
        self.size -= 1
        return v

    def remove(self, v: int) -> bool:
        prev = None
        cur = self.head
        while cur is not None:
            if cur.val == v:
                if prev is None:
                    self.head = cur.next
                else:
                    prev.next = cur.next
                self.size -= 1
                return True
            prev = cur
            cur = cur.next
        return False

    def reverse(self) -> None:
        prev = None
        cur = self.head
        while cur:
            nxt = cur.next
            cur.next = prev
            prev = cur
            cur = nxt
        self.head = prev

    def find(self, v: int) -> Optional[Node]:
        cur = self.head
        while cur is not None and cur.val != v:
            cur = cur.next
        return cur

    def to_list(self) -> list[int]:
        out = []
        cur = self.head
        while cur is not None:
            out.append(cur.val)
            cur = cur.next
        return out


class TreeNode:
    def __init__(self, key: int) -> None:
        self.key = key
        self.left = None
        self.right = None


def insert(root: Optional[TreeNode], key: int) -> TreeNode:
    if root is None:
        return TreeNode(key)
    if key < root.key:
        root.left = insert(root.left, key)
    elif key > root.key:
        root.right = insert(root.right, key)
    return root


def min_node(root: TreeNode) -> TreeNode:
    cur = root
    while cur.left is not None:
        cur = cur.left
    return cur


def delete(root: Optional[TreeNode], key: int) -> Optional[TreeNode]:
    if root is None:
        return None
    if key < root.key:
        root.left = delete(root.left, key)
    elif key > root.key:
        root.right = delete(root.right, key)
    else:
        if root.left is None:
            return root.right
        if root.right is None:
            return root.left
        m = min_node(root.right)
        root.key = m.key
        root.right = delete(root.right, m.key)
    return root


def inorder(root: Optional[TreeNode], out: list[int]) -> None:
    if root is not None:
        inorder(root.left, out)
        out.append(root.key)
        inorder(root.right, out)


def height(root: Optional[TreeNode]) -> int:
    if root is None:
        return 0
    return 1 + max(height(root.left), height(root.right))


def contains(root: Optional[TreeNode], key: int) -> bool:
    while root is not None:
        if key == root.key:
            return True
        root = root.left if key < root.key else root.right
    return False


def smallest(root: Optional[TreeNode]) -> Optional[int]:
    if root is None:
        return None
    return min_node(root).key


def main() -> None:
    ll = LinkedList()
    root: Optional[TreeNode] = None
'''


def body(seed, n):
    r = random.Random(seed)
    L = []
    for _ in range(n):
        v = r.randint(0, 15)
        op = r.randrange(16)
        if op == 0:
            L.append(f"    ll.push_front({v})")
        elif op == 1:
            L.append(f"    ll.push_back({v})")
        elif op == 2:
            L.append("    print(ll.pop_front(), ll.size)")
        elif op == 3:
            L.append(f"    print(ll.remove({v}), ll.to_list())")
        elif op == 4:
            L.append("    ll.reverse()")
        elif op == 5:
            L.append(f"    f = ll.find({v})")
            L.append("    print(f is None, f.val if f is not None else -1)")
        elif op == 6:
            L.append("    print(ll.to_list(), ll.size)")
        elif op in (7, 8, 9):
            L.append(f"    root = insert(root, {v})")
        elif op in (10, 11):
            L.append(f"    root = delete(root, {v})")
        elif op == 12:
            L.append("    out: list[int] = []")
            L.append("    inorder(root, out)")
            L.append("    print(out, height(root))")
        elif op == 13:
            L.append(f"    print(contains(root, {v}), smallest(root))")
        elif op == 14:
            L.append("    print(root is None, ll.head is None, ll.find(3) is not None)")
        else:
            L.append("    print(root.key if root else None, ll.head.val if ll.head else None)")
    return "\n".join(L) + "\n"


def program(seed, n):
    # `out` est redéclarée plusieurs fois : on la déclare une seule fois en tête
    src = HEADER + "    f: Optional[Node] = None\n    out: list[int] = []\n" + body(seed, n).replace("    out: list[int] = []\n", "    out = []\n")
    return src + "    print(ll.to_list())\n\n\nif __name__ == \"__main__\":\n    main()\n"


def run_seed(seed, n, target):
    src = program(seed, n)
    path = Path(tempfile.mkdtemp(prefix="fuzzo_")) / "prog.py"
    path.write_text(src, encoding="utf-8")
    try:
        expected = python_output(path)
    except RuntimeError as ex:
        return [f"seed {seed}: le programme Python échoue : {str(ex)[:200]}"], 0, src
    try:
        code = transpile(src, target)
    except Unsupported as ex:
        return [f"seed {seed}: Unsupported : {ex}"], 0, src
    got, err = build_and_run(code, target)
    if err:
        return [f"seed {seed}: {err[:1500]}"], 0, src
    got, exp = got.replace("\r\n", "\n").splitlines(), expected.splitlines()
    bad = [f"seed {seed}: {len(got)} lignes obtenues, {len(exp)} attendues"] if len(got) != len(exp) else []
    for i, (a, b) in enumerate(zip(exp, got)):
        if a != b:
            bad.append(f"seed {seed} ligne {i + 1}:\n      Python={a}\n      {target}={b}")
    return bad, len(exp), src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["cpp", "kotlin"], required=True)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--n", type=int, default=70)
    a = ap.parse_args()
    total, failures = 0, []
    for seed in range(a.first, a.first + a.seeds):
        bad, n, src = run_seed(seed, a.n, a.target)
        total += n
        failures += bad
        print(f"seed {seed} : {n} lignes comparées, {len(bad)} écart(s)", flush=True)
        if bad and not (ROOT / "tests" / "fuzz_failure.py").exists():
            (ROOT / "tests" / "fuzz_failure.py").write_text(src, encoding="utf-8")
    for f in failures[:12]:
        print("  ÉCART", f)
    print(f"\n{total} lignes comparées, {len(failures)} écart(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

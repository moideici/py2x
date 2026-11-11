from typing import Optional


class TreeNode:
    def __init__(self, key: int) -> None:
        self.key = key
        self.left: Optional[TreeNode] = None
        self.right: Optional[TreeNode] = None


def insert(root: Optional[TreeNode], key: int) -> TreeNode:
    if root is None:
        return TreeNode(key)
    if key < root.key:
        root.left = insert(root.left, key)
    elif key > root.key:
        root.right = insert(root.right, key)
    return root


def inorder(root: Optional[TreeNode], out: list[int]) -> None:
    if root is None:
        return
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


def main() -> None:
    root: Optional[TreeNode] = None
    for k in [50, 30, 70, 20, 40, 60, 80, 30]:
        root = insert(root, k)
    out: list[int] = []
    inorder(root, out)
    print(out, height(root))
    print(contains(root, 60), contains(root, 65))


if __name__ == "__main__":
    main()

def merge_sort(arr: list[int]) -> list[int]:
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    merged: list[int] = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


def quick_sort(arr: list[int]) -> list[int]:
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    less = [x for x in arr if x < pivot]
    equal = [x for x in arr if x == pivot]
    more = [x for x in arr if x > pivot]
    return quick_sort(less) + equal + quick_sort(more)


def insertion_sort(arr: list[int]) -> None:
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key


def is_sorted(arr: list[int]) -> bool:
    return all(arr[i] <= arr[i + 1] for i in range(len(arr) - 1))


def main() -> None:
    data = [38, 27, 43, 3, 9, 82, 10, 3, -5]
    print(merge_sort(data))
    print(quick_sort(data))
    copy = data[:]
    insertion_sort(copy)
    print(copy, is_sorted(copy), is_sorted(data))


if __name__ == "__main__":
    main()

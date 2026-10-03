"""Reference solution. CI asserts this passes every test in `tests.py`."""


def best_value(items: list[tuple[int, int]], capacity: int) -> int:
    """Return the most value that fits in the capacity.

    `best[c]` is the most value achievable with capacity exactly c or less, and
    the table is rebuilt item by item: for each item, every capacity it fits in
    gets the choice of taking it or not.

    **The inner loop runs downwards, and that is the whole 0/1 constraint.**
    Going upwards, `best[c - weight]` has already been updated for this item, so
    the item can be taken twice -- which is the unbounded knapsack, a different
    and easier problem. One `reversed` is the difference between "each item once"
    and "each item as often as you like", and nothing else in the code says
    which problem is being solved.

    Greedy fails here, and it is worth being able to show why rather than
    asserting it: by value-per-weight on `[(10, 60), (20, 100), (30, 120)]` with
    capacity 50 it takes the first two for 160, and the last two are worth 220.
    The ratio is a good heuristic precisely because it is *nearly* right, which
    is the worst property a wrong answer can have.

    The one-dimensional table is the two-dimensional one with the item axis
    collapsed, available because each row reads only the row above. It costs the
    ability to say which items were chosen -- for that, keep the full table and
    walk back.
    """
    best = [0] * (capacity + 1)
    for weight, value in items:
        for remaining in reversed(range(weight, capacity + 1)):
            best[remaining] = max(best[remaining], best[remaining - weight] + value)
    return best[capacity]

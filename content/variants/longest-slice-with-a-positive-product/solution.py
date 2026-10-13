"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_positive_slice(numbers: list[int]) -> int:
    """Return the length of the longest slice with a positive product.

    The maximum-product solution carries two products, because a negative
    value turns the smallest into the largest. This carries two lengths for
    the same reason: `positive` is the longest slice ending at the current
    value whose product is positive, and `negative` the longest whose product
    is negative. Zero means there is no such slice.

    A positive value extends both. A negative value extends both and swaps
    them. A zero ends everything.

    The one subtlety is that extending is only possible if there is
    something to extend. A positive value can always start a positive slice
    on its own, so `positive + 1` is right even from zero. It cannot start a
    negative one, so `negative` stays at zero if it was zero. The negative
    case is the mirror image.

    No product is ever computed, which is the point: with values up to a
    thousand million, the product of the whole list would have close to a
    million digits.
    """
    best = positive = negative = 0
    for value in numbers:
        if value == 0:
            positive = negative = 0
        elif value > 0:
            positive += 1
            negative = negative + 1 if negative else 0
        else:
            positive, negative = (negative + 1 if negative else 0), positive + 1
        best = max(best, positive)
    return best

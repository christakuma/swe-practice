"""Reference solution. CI asserts this passes every test in `tests.py`."""


def trapped_water(heights: list[int]) -> int:
    """Return the total water trapped between the bars.

    The water above a bar reaches the lower of the tallest bar on its left
    and the tallest on its right. Two pointers move inward, each carrying the
    tallest bar seen from its own end.

    The side with the lower maximum is the one that can be settled: its
    level is that maximum, because the other side is known to hold something
    at least as tall. So that bar's water is added and that pointer moves.
    """
    left, right = 0, len(heights) - 1
    tallest_left = tallest_right = 0
    water = 0
    while left <= right:
        if tallest_left <= tallest_right:
            tallest_left = max(tallest_left, heights[left])
            water += tallest_left - heights[left]
            left += 1
        else:
            tallest_right = max(tallest_right, heights[right])
            water += tallest_right - heights[right]
            right -= 1
    return water

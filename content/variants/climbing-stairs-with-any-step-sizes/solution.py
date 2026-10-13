"""Reference solution. CI asserts this passes every test in `tests.py`."""


def ways_to_climb(steps: int, sizes: list[int]) -> int:
    """Count the distinct ways to climb `steps` steps using the given sizes.

    `ways[height]` is the number of ordered sequences reaching that height.
    The last move of any such sequence was one of the sizes, and what came
    before it is a sequence reaching `height - size`, so the entry is the sum
    of those. The height is the outer loop, which is what makes order count:
    every size is offered as the last move at every height.
    """
    ways = [1] + [0] * steps
    for height in range(1, steps + 1):
        ways[height] = sum(ways[height - size] for size in sizes if size <= height)
    return ways[steps]

"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator

from solution import find_minimum


class Watched(list[int]):
    """A list that counts how many of its values have been read.

    The only way to hold a solution to `O(log n)` from the outside: two
    million values are scanned in a few milliseconds, so no time limit can
    tell a scan from a search, and a count can.

    Subscripting and iteration are counted a value at a time. **The methods
    that read the whole list are charged for the whole list**, because they
    are where a count kept in `__getitem__` goes blind: `in`, `index`,
    `count`, `copy`, `reversed`, `+` and `*` all walk every value inside the
    interpreter and never call it.
    """

    reads = 0

    def __getitem__(self, index):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN204
        if isinstance(index, slice):
            self.reads += len(range(*index.indices(len(self))))
        else:
            self.reads += 1
        return super().__getitem__(index)

    def __iter__(self) -> Iterator[int]:
        for position in range(len(self)):
            yield self[position]

    def __contains__(self, value: object) -> bool:
        self.reads += len(self)
        return super().__contains__(value)

    def index(self, value: int, *bounds: int) -> int:  # type: ignore[override]
        self.reads += len(self)
        return super().index(value, *bounds)

    def count(self, value: int) -> int:
        self.reads += len(self)
        return super().count(value)

    def copy(self) -> list[int]:
        self.reads += len(self)
        return super().copy()

    def __reversed__(self) -> Iterator[int]:
        self.reads += len(self)
        return super().__reversed__()

    def __add__(self, other: list[int]) -> list[int]:  # type: ignore[override]
        self.reads += len(self)
        return super().__add__(other)

    def __mul__(self, times: int) -> list[int]:  # type: ignore[override]
        self.reads += len(self)
        return super().__mul__(times)

    def __rmul__(self, times: int) -> list[int]:  # type: ignore[override]
        self.reads += len(self)
        return super().__rmul__(times)


def rotations(values: list[int]) -> list[list[int]]:
    """Every left rotation of `values`."""
    return [values[k:] + values[:k] for k in range(len(values))]


def test_finds_the_minimum_after_a_rotation() -> None:
    """Finds the smallest value in a rotated list."""
    assert find_minimum([3, 4, 5, 1, 2]) == 1
    assert find_minimum([4, 5, 6, 7, 0, 1, 2]) == 0


def test_handles_a_list_that_was_not_rotated() -> None:
    """Returns the first element when the rotation is zero.

    A solution that compares the middle with `numbers[low]` instead of
    `numbers[high]` reads an unrotated list as if the step-down were to the
    right, and walks off toward the largest value.
    """
    assert find_minimum([11, 13, 15, 17]) == 11
    assert find_minimum([1, 2, 3, 4, 5, 6, 7, 8]) == 1


def test_handles_a_single_element() -> None:
    """Returns the only value in a one-element list."""
    assert find_minimum([1]) == 1


def test_handles_two_elements_either_way_round() -> None:
    """Handles both arrangements of a two-element list.

    The window of width two is where `low = mid` instead of `low = mid + 1`
    stops making progress and the search hangs rather than answering wrongly.
    """
    assert find_minimum([1, 2]) == 1
    assert find_minimum([2, 1]) == 1


def test_handles_the_minimum_at_the_very_end() -> None:
    """Finds the minimum when the rotation puts it in the last position."""
    assert find_minimum([2, 3, 4, 5, 1]) == 1


def test_handles_the_minimum_just_past_the_middle() -> None:
    """Finds the minimum sitting immediately right of the midpoint.

    `high = mid - 1` written for symmetry with the other branch steps over the
    answer exactly here.
    """
    assert find_minimum([4, 5, 6, 1, 2, 3]) == 1
    assert find_minimum([5, 6, 7, 8, 1, 2, 3, 4]) == 1


def test_handles_negative_values() -> None:
    """Finds the minimum when the values straddle zero."""
    assert find_minimum([3, 4, -5, -2, 0]) == -5
    assert find_minimum([-9, -4, 0, 7]) == -9


def test_finds_the_minimum_for_every_rotation_at_every_small_size() -> None:
    """Agrees for every size up to forty and every rotation of it.

    Eight hundred cases. Every known failure of this kata -- the unrotated
    list, the off-by-one that discards the answer, the branch that fails to
    narrow -- lives at a particular (size, rotation) pair, and enumerating
    them is cheaper than arguing about which pairs are dangerous.
    """
    for size in range(1, 41):
        base = [value * 3 - 7 for value in range(size)]
        for rotated in rotations(base):
            assert find_minimum(rotated) == base[0], rotated


def test_leaves_the_input_alone() -> None:
    """Does not sort or mutate the list it was given."""
    numbers = [3, 4, 5, 1, 2]
    original = list(numbers)

    find_minimum(numbers)

    assert numbers == original


def test_searches_a_large_list_in_logarithmic_time() -> None:
    """Reads at most a hundred of two million values, wherever the minimum is.

    Halving two million takes twenty-one rounds, and each round reads two
    values. `min()` reads all of them. This test used to check the answer
    alone and say so -- "a linear scan also answers this" -- which left the
    one thing the prompt asks for ungraded.
    """
    size = 2_000_000
    base = list(range(size))
    for pivot in (0, 1, 1_234_567, size // 2, size - 1):
        rotated = Watched(base[pivot:] + base[:pivot])
        rotated.reads = 0

        assert find_minimum(rotated) == 0, pivot
        assert rotated.reads <= 100, f"read {rotated.reads} values"

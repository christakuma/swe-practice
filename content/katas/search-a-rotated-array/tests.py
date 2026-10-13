"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator

from solution import search


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


def test_finds_a_value_in_the_rotated_tail() -> None:
    """Finds a target that sits after the rotation point."""
    assert search([4, 5, 6, 7, 0, 1, 2], 0) == 4


def test_finds_a_value_in_the_rotated_head() -> None:
    """Finds a target that sits before the rotation point."""
    assert search([4, 5, 6, 7, 0, 1, 2], 6) == 2


def test_reports_an_absent_value() -> None:
    """Returns -1 for a value that is not present."""
    assert search([4, 5, 6, 7, 0, 1, 2], 3) == -1


def test_handles_an_empty_list() -> None:
    """Returns -1 for an empty list without raising."""
    assert search([], 5) == -1


def test_handles_a_single_element() -> None:
    """Finds or rejects the only value in a one-element list."""
    assert search([1], 1) == 0
    assert search([1], 0) == -1


def test_classifies_the_sorted_half_at_a_window_of_two() -> None:
    """Finds the target in a two-element rotated list.

    The smallest case that separates `numbers[low] <= numbers[mid]` from the
    strict version: `mid` rounds down to `low`, so the two are the same
    element, and `<` wrongly concludes the left half is unsorted and discards
    the half holding the answer. Verified against that bug, which returns -1
    here and passes every other hand-picked case in this file.
    """
    assert search([1, 0], 0) == 1
    assert search([1, 0], 1) == 0


def test_handles_a_list_that_was_not_rotated() -> None:
    """Searches a fully sorted list, which is a rotation of zero."""
    assert search([1, 2, 3, 4, 5], 1) == 0
    assert search([1, 2, 3, 4, 5], 5) == 4
    assert search([1, 2, 3, 4, 5], 3) == 2
    assert search([1, 2, 3, 4, 5], 6) == -1


def test_finds_the_values_at_both_ends() -> None:
    """Finds the first and last elements of a rotated list."""
    numbers = [5, 6, 7, 1, 2, 3, 4]

    assert search(numbers, 5) == 0
    assert search(numbers, 4) == 6


def test_rejects_values_outside_the_range() -> None:
    """Returns -1 for values below the minimum and above the maximum."""
    numbers = [4, 5, 6, 7, 0, 1, 2]

    assert search(numbers, -1) == -1
    assert search(numbers, 8) == -1


def test_handles_negative_values() -> None:
    """Searches a rotated list whose values straddle zero."""
    numbers = [3, 7, -9, -4, 0]

    assert search(numbers, -9) == 2
    assert search(numbers, 3) == 0
    assert search(numbers, -5) == -1


def test_finds_every_value_for_every_rotation_at_every_small_size() -> None:
    """Finds every present value, for every rotation, at every size up to forty.

    Around twenty thousand searches. The comparison bug, the off-by-one window
    updates and the mis-scoped range checks each fail only at particular
    (size, rotation, target) triples, so enumerating beats choosing.
    """
    for size in range(1, 41):
        base = [value * 3 - 7 for value in range(size)]
        for k in range(size):
            rotated = base[k:] + base[:k]
            for index, value in enumerate(rotated):
                assert search(rotated, value) == index, (rotated, value)


def test_rejects_every_absent_value_for_every_rotation() -> None:
    """Returns -1 for values in the gaps, at every size and rotation.

    The values step by three, so every `value + 1` is absent. A search that
    settles into the wrong half tends to return an index rather than -1.
    """
    for size in range(1, 31):
        base = [value * 3 - 7 for value in range(size)]
        absent = [value + 1 for value in base] + [base[0] - 1, base[-1] + 1]
        for k in range(size):
            rotated = base[k:] + base[:k]
            for value in absent:
                assert search(rotated, value) == -1, (rotated, value)


def test_leaves_the_input_alone() -> None:
    """Does not sort or mutate the list it was given."""
    numbers = [4, 5, 6, 7, 0, 1, 2]
    original = list(numbers)

    search(numbers, 0)

    assert numbers == original


def test_searches_a_large_list() -> None:
    """Finds and rejects values in a list of two million elements."""
    size = 2_000_000
    pivot = 1_234_567
    base = list(range(0, size * 2, 2))
    rotated = base[pivot:] + base[:pivot]

    assert rotated[search(rotated, 0)] == 0
    assert rotated[search(rotated, base[-1])] == base[-1]
    assert search(rotated, 1) == -1


def test_reads_only_a_handful_of_values() -> None:
    """Reads at most three hundred of two million values per search.

    Halving two million takes twenty-one rounds. The single-pass search reads
    up to five values a round and finding the rotation first reads fewer, so
    three hundred leaves either plenty of room. A scan reads two million, and
    so do `in` and `index` -- which were an accepted answer here until this
    test, because the one above checks what comes back and not how.
    """
    size = 2_000_000
    pivot = 1_234_567
    base = list(range(0, size * 2, 2))
    plain = base[pivot:] + base[:pivot]
    rotated = Watched(plain)
    present = (base[0], base[-1], plain[0], plain[-1], base[777_777], base[1_999_000])
    absent = (1, -5, size * 2 + 1, plain[0] + 1)

    for target in present:
        rotated.reads = 0
        assert search(rotated, target) == plain.index(target), target
        assert rotated.reads <= 300, f"read {rotated.reads} values"
    for target in absent:
        rotated.reads = 0
        assert search(rotated, target) == -1, target
        assert rotated.reads <= 300, f"read {rotated.reads} values"

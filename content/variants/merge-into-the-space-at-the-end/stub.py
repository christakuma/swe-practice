"""Your solution goes here. The tests import `merge_into` from this module."""


def merge_into(first: list[int], count: int, second: list[int]) -> None:
    """Merge `second` into `first` in place, using the room at its end.

    Args:
        first: a list whose first `count` entries are sorted values and whose
            remaining `len(second)` entries are spare slots holding junk.
            Modified in place.
        count: how many real values `first` holds.
        second: a sorted list. Must not be modified.

    Returns:
        None. Afterwards `first` holds every value of both, ascending.
    """
    raise NotImplementedError

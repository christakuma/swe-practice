"""Reference solution. CI asserts this passes every test in `tests.py`."""


def merge_into(first: list[int], count: int, second: list[int]) -> None:
    """Merge `second` into `first` in place, using the room at its end.

    Merged from the back. The largest value overall is the larger of the two
    lists' last values, and the place it belongs -- the final slot of `first`
    -- is spare. Writing it there frees nothing and destroys nothing, and the
    same is true of every step after: the write position is always at or
    beyond the read position in `first`, because the gap between them is
    exactly the number of values of `second` still to place.

    The loop runs until `second` is used up. If `first`'s values run out
    earlier, the rest of `second` is copied down. If `second` runs out
    earlier, what remains of `first` is already where it should be.
    """
    read = count - 1
    other = len(second) - 1
    write = len(first) - 1
    while other >= 0:
        if read >= 0 and first[read] > second[other]:
            first[write] = first[read]
            read -= 1
        else:
            first[write] = second[other]
            other -= 1
        write -= 1

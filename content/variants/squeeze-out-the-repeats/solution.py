"""Reference solution. CI asserts this passes every test in `tests.py`."""


def remove_duplicates(numbers: list[int]) -> int:
    """Move the distinct values to the front of a sorted list and count them.

    The move-zeroes compaction with a different test. `write` is where the
    next kept value goes, and everything before it is the answer so far: the
    distinct values seen, in order.

    Because the list is sorted, a value is new exactly when it differs from
    the last value kept, which is `numbers[write - 1]`. Comparing against the
    kept prefix rather than against the previous element read means the test
    stays right even though the list is being overwritten as it is scanned.

    `write` never passes the read position, so nothing is overwritten before
    it has been read. When the scan ends, `write` is the count.
    """
    write = 0
    for value in numbers:
        if write == 0 or value != numbers[write - 1]:
            numbers[write] = value
            write += 1
    return write

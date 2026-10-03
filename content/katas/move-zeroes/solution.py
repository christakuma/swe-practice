"""Reference solution. CI asserts this passes every test in `tests.py`."""


def move_zeroes(numbers: list[int]) -> None:
    """Move every zero to the end of the list, in place.

    Two pointers over one list: `write` is where the next non-zero belongs,
    `index` is where we are reading. Everything before `write` is already the
    non-zero prefix, in its original order, which is the invariant the whole
    thing rests on.

    The second loop is not a shortcut. Having copied every non-zero element
    forward, positions from `write` onwards still hold whatever was there
    before -- duplicates of elements now earlier in the list -- so they have to
    be overwritten with zeros. Swapping instead of copying avoids the second
    loop and does more writes; both are standard and the copy version is easier
    to be sure about.

    "In place" is the real constraint. Building a new list of non-zeros and
    padding it is correct, obvious, and O(n) extra space -- and the function
    returns None, so assigning to a local name would not even be visible to the
    caller. Mutating the argument is the point.
    """
    write = 0
    for index in range(len(numbers)):
        if numbers[index] != 0:
            numbers[write] = numbers[index]
            write += 1
    for index in range(write, len(numbers)):
        numbers[index] = 0

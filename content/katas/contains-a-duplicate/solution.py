"""Reference solution. CI asserts this passes every test in `tests.py`."""


def has_duplicate(numbers: list[int]) -> bool:
    """Return whether any value appears more than once.

    One pass, one set, and -- the part the banned one-liner gives up -- an
    **early return**. The question is existential, so the first repeat settles
    it; there is no reason to read the rest of the list or to finish building a
    set of everything in it.

    That matters more than it looks. `len(set(numbers)) != len(numbers)` is
    O(n) time and O(n) space *always*, where this is O(n) in the worst case and
    O(1) on a list that starts with two equal values. Same asymptotics, and a
    different function: one of them can answer a question about a billion-element
    list by looking at two of them.

    Checking membership before inserting is what makes the first comparison
    meaningful -- insert first and every element finds itself.

    The O(1)-space alternative is to sort and then compare neighbours, since
    equal values become adjacent. It costs O(n log n) time, mutates the
    caller's list unless you copy it (which gives the space straight back), and
    loses the early exit. Worth knowing as the answer to "what if memory is the
    binding constraint", and worth not reaching for otherwise.
    """
    seen: set[int] = set()
    for value in numbers:
        if value in seen:
            return True
        seen.add(value)
    return False

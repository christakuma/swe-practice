"""Reference solution. CI asserts this passes every test in `tests.py`."""


def is_balanced(text: str) -> bool:
    """Whether some reading of the stars leaves the brackets balanced.

    `fewest` and `most` are the smallest and largest number of brackets that
    could be open after each character, over every reading of the stars so
    far. Every count between them is reachable too, which is why two numbers
    are enough.

    `most < 0` means a closer has arrived that no reading can match. `fewest`
    is clamped at zero because a reading that would take it negative is one
    that used a star as a closer with nothing open -- not a valid reading,
    so it is dropped rather than counted. The string balances if zero is
    still in the range at the end.
    """
    fewest = most = 0
    for character in text:
        if character == "(":
            fewest += 1
            most += 1
        elif character == ")":
            fewest -= 1
            most -= 1
        else:
            fewest -= 1
            most += 1
        if most < 0:
            return False
        fewest = max(fewest, 0)
    return fewest == 0

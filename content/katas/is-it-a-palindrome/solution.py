"""Reference solution. CI asserts this passes every test in `tests.py`."""


def is_palindrome(text: str) -> bool:
    """Return whether `text` reads the same both ways, ignoring case and
    non-alphanumeric characters.

    Two pointers walking inward. The only real content is what happens to the
    characters that do not count: they are skipped **in place**, by advancing
    the pointer, rather than removed by building a filtered copy.

    That is the whole reason for the O(1) space bound. The filtered version is
    shorter and perfectly correct:

        cleaned = [c.lower() for c in text if c.isalnum()]
        return cleaned == cleaned[::-1]

    ...and it allocates two sequences the size of the input. On a large string
    that is the difference between a constant and a megabyte, for a question
    whose answer is one bit.

    Both skip loops are guarded by `low < high`. Without it a string of pure
    punctuation walks a pointer off the end -- and the `while low < high` at
    the top cannot help, because the skipping happens inside an iteration that
    has already begun.

    The empty case needs no branch: the outer loop never runs and True is the
    right answer, which is also the right answer for a string with no
    alphanumerics at all. An empty sequence reads the same both ways.

    `isalnum` and `lower` are the right primitives rather than an explicit
    a-z/0-9 range check, because they are defined over Unicode -- so accented
    letters and non-Latin scripts classify and fold correctly instead of being
    silently treated as punctuation.
    """
    low, high = 0, len(text) - 1
    while low < high:
        while low < high and not text[low].isalnum():
            low += 1
        while low < high and not text[high].isalnum():
            high -= 1
        if text[low].lower() != text[high].lower():
            return False
        low += 1
        high -= 1
    return True

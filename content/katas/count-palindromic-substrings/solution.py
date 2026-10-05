"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_palindromes(text: str) -> int:
    """Count the palindromic substrings, counting positions separately.

    The same centre expansion as `longest-palindromic-substring`, and the
    interesting part is how little changes. There, each centre produced one
    answer -- its widest palindrome -- and the widest was all that mattered.
    Here every *step* of the expansion matters, because each successful step is
    itself a distinct palindromic substring, one character wider at each end
    than the last.

    So the count happens **inside** the expansion loop rather than after it.
    That is the whole difference between the two katas: the generator is
    identical and one consumes only its final value while the other consumes
    all of them.

    Both centre kinds, as before: n character-centres and n-1 gap-centres.
    Counting only the odd centres gives a number that is too small and entirely
    plausible -- "aaa" comes out as 4 instead of 6 -- which is worse than a
    crash.

    Nothing needs to deduplicate. Identical substrings at different positions
    are different substrings by the problem's definition, and each is found by
    exactly one centre, so each is counted exactly once with no bookkeeping.
    """

    def count_from(low: int, high: int) -> int:
        found = 0
        while low >= 0 and high < len(text) and text[low] == text[high]:
            found += 1
            low -= 1
            high += 1
        return found

    return sum(
        count_from(centre, centre) + count_from(centre, centre + 1)
        for centre in range(len(text))
    )

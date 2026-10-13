"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_longest_increasing(numbers: list[int]) -> int:
    """Return how many strictly increasing subsequences are of the greatest length.

    The quadratic table with a second column. `lengths[i]` is the longest
    increasing subsequence ending at position `i`, as before; `ways[i]` is how
    many subsequences of that length end there.

    For each earlier position `j` holding a smaller value, extending its runs
    by `i` gives runs of length `lengths[j] + 1`:

    - longer than anything `i` has yet: they are the new best, and there are
      exactly `ways[j]` of them -- replace;
    - the same length: they are further ways to reach it -- add;
    - shorter: irrelevant.

    The longest runs may end at several different positions, so the answer
    sums `ways` over every position that reaches the maximum.
    """
    if not numbers:
        return 1
    lengths = [1] * len(numbers)
    ways = [1] * len(numbers)
    for i, value in enumerate(numbers):
        for j in range(i):
            if numbers[j] < value:
                if lengths[j] + 1 > lengths[i]:
                    lengths[i] = lengths[j] + 1
                    ways[i] = ways[j]
                elif lengths[j] + 1 == lengths[i]:
                    ways[i] += ways[j]
    longest = max(lengths)
    return sum(
        count for length, count in zip(lengths, ways, strict=True) if length == longest
    )

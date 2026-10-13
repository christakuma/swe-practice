"""Reference solution. CI asserts this passes every test in `tests.py`."""


def remove(
    intervals: list[tuple[int, int]],
    gone: tuple[int, int],
) -> list[tuple[int, int]]:
    """Remove `gone` from a sorted list of non-overlapping half-open intervals.

    Each interval is handled alone. One that ends at or before the removal
    starts, or starts at or after it ends, is untouched -- `<=` and `>=`
    because half-open intervals that touch share nothing. Otherwise up to two
    pieces survive, and each is kept only if it has positive length.
    """
    cut_from, cut_to = gone
    kept: list[tuple[int, int]] = []
    for start, end in intervals:
        if end <= cut_from or start >= cut_to:
            kept.append((start, end))
            continue
        if start < cut_from:
            kept.append((start, cut_from))
        if end > cut_to:
            kept.append((cut_to, end))
    return kept

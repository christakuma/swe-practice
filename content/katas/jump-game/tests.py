"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import can_reach_the_end


def test_reaches_the_end_of_a_simple_list() -> None:
    """Reaches the end when the jumps are long enough."""
    assert can_reach_the_end([2, 3, 1, 1, 4]) is True


def test_is_stopped_by_a_zero() -> None:
    """Returns False when a zero blocks the only route."""
    assert can_reach_the_end([3, 2, 1, 0, 4]) is False


def test_jumps_over_a_zero() -> None:
    """Passes a zero when an earlier jump is long enough to clear it.

    The 5 at position 1 clears every zero after it. A solution that stops at
    the first zero it meets says False.
    """
    assert can_reach_the_end([2, 5, 0, 0]) is True


def test_handles_a_single_position() -> None:
    """Returns True when the start is already the end, even with a zero."""
    assert can_reach_the_end([0]) is True


def test_handles_a_zero_at_the_very_end() -> None:
    """Returns True when the blocking zero is the destination itself.

    Position 1 is the end, so its jump length never matters. A solution that
    requires the final jump to be positive says False.
    """
    assert can_reach_the_end([1, 0]) is True


def test_is_stopped_by_a_zero_at_the_start() -> None:
    """Returns False when the first position cannot be left."""
    assert can_reach_the_end([0, 1]) is False


def test_handles_steps_of_exactly_one() -> None:
    """Reaches the end one step at a time."""
    assert can_reach_the_end([1, 1, 1, 1]) is True


def test_handles_one_long_jump_over_everything() -> None:
    """Clears the whole list in a single jump."""
    assert can_reach_the_end([5, 0, 0, 0, 0, 0]) is True


def test_handles_a_long_reachable_list_quickly() -> None:
    """Crosses a list far too long for a quadratic reachability table.

    Fifty thousand single steps. Marking every position reachable from every
    other is 1.25 billion operations; the frontier is one pass.
    """
    assert can_reach_the_end([1] * 50_000) is True


def test_handles_a_long_blocked_list_quickly() -> None:
    """Stops at a blockage half way along a very long list."""
    jumps = [1] * 25_000 + [0] + [1] * 25_000

    assert can_reach_the_end(jumps) is False

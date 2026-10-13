"""Your solution goes here. The tests import `ways_to_make` from here."""


def ways_to_make(coins: list[int], amount: int) -> int:
    """Count the combinations of coins that add up to `amount`.

    Each coin value may be used any number of times, and the order coins are
    taken in does not matter.

    Args:
        coins: the available coin values. Distinct and positive.
        amount: the total to make. Zero or more.

    Returns:
        How many different multisets of coins sum to `amount`. One for an
        amount of zero.
    """
    raise NotImplementedError

"""Your solution goes here. The tests import `ways_to_climb` from here."""


def ways_to_climb(steps: int, sizes: list[int]) -> int:
    """Count the distinct ways to climb `steps` steps using the given sizes.

    Args:
        steps: how many steps there are. Zero or more.
        sizes: the step sizes a single move may take. Distinct and positive,
            in no particular order.

    Returns:
        The number of distinct sequences of sizes that sum to exactly
        `steps`. One for zero steps; zero when no sequence fits.
    """
    raise NotImplementedError

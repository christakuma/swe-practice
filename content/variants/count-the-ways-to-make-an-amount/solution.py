"""Reference solution. CI asserts this passes every test in `tests.py`."""


def ways_to_make(coins: list[int], amount: int) -> int:
    """Count the combinations of coins that add up to `amount`.

    `ways[total]` is the number of combinations using only the coins brought
    in so far. Each coin is added to the table for every total before the
    next coin is looked at, so a combination is only ever built in one order
    -- the order the coins are listed in -- and is counted once.

    With the loops the other way round every coin could be the last one added
    at every total, and the table would count orderings instead.
    """
    ways = [1] + [0] * amount
    for coin in coins:
        for total in range(coin, amount + 1):
            ways[total] += ways[total - coin]
    return ways[amount]

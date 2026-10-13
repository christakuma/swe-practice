"""Reference solution. CI asserts this passes every test in `tests.py`."""

import math


def fewest_coins(coins: list[int], amount: int) -> int:
    """Return the fewest coins from the purse that add up to `amount`.

    The same table as the unlimited version -- `best[a]` is the fewest coins
    making `a` -- filled in the other order. The coins are the outer loop, so
    each coin is offered to the table once. The amounts run **downwards**, so
    that when `best[target - coin]` is read it still describes selections made
    from the earlier coins only. Run them upwards and that entry may already
    include this coin, which spends it twice.

    Equal values need no special handling: they are separate turns of the
    outer loop, which is exactly what makes them separate coins.
    """
    best = [0] + [math.inf] * amount
    for coin in coins:
        for target in range(amount, coin - 1, -1):
            best[target] = min(best[target], best[target - coin] + 1)
    return -1 if best[amount] == math.inf else int(best[amount])

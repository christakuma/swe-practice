"""Reference solution. CI asserts this passes every test in `tests.py`."""

import math


def fewest_coins(coins: list[int], amount: int) -> int:
    """Return the fewest coins that add up to `amount`.

    Bottom-up over every amount from 1 to the target. For each one, try every
    coin: if the coin fits, the best is one more than the best for the remainder.
    `best[0] = 0` -- no coins make nothing -- and everything else starts at
    infinity meaning "not reachable yet".

    Greedy -- take the largest coin that fits, repeat -- is the solution everyone
    writes first, and it is wrong for general coin sets. On `[1, 3, 4]` making 6
    it takes 4, then 1, then 1, for three coins; two 3s is the answer. It happens
    to be correct for the coins in your pocket, because real currency systems are
    deliberately designed so that it is, which is why the mistake survives
    testing against examples that look realistic.

    Infinity rather than a sentinel like -1 inside the table: `best[a - c] + 1`
    then stays a correct arithmetic statement about an unreachable amount, and
    only the final answer has to be translated. A -1 sentinel in the table has to
    be checked at every read, and the check is easy to forget on one branch.
    """
    best = [0] + [math.inf] * amount
    for target in range(1, amount + 1):
        for coin in coins:
            if coin <= target:
                best[target] = min(best[target], best[target - coin] + 1)
    return -1 if best[amount] == math.inf else int(best[amount])

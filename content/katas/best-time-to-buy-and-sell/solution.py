"""Reference solution. CI asserts this passes every test in `tests.py`."""


def max_profit(prices: list[int]) -> int:
    """Return the largest profit from one buy followed by one later sell.

    The naive version fixes a buy day and scans forward for the best sell day,
    which is O(n^2). Turning the question around is what collapses it: fix the
    **sell** day and ask what the best buy day before it was. That has a
    one-number answer -- the cheapest price so far -- and walking left to right
    means you already have it.

    So the whole state is two running values, and the scan is a single pass.
    This is the same shape as Kadane's algorithm in `maximum-subarray`: carry
    the best answer *ending here* alongside the best answer *anywhere*, and
    never look backwards.

    **The order of the two statements does not matter here, and the reason is
    worth more than the rule.** `best` is computed against `cheapest` as it
    stood before today, so today cannot be both the buy and the sell day.
    Update `cheapest` first and today *can* trade with itself -- but that trade
    is worth `price - price`, exactly 0, and `best` already starts at 0 and
    only moves up. The illegal option is permitted and is never an improvement,
    so both orderings are correct.

    That is a stronger kind of safety than an ordering convention: the
    constraint is enforced by the arithmetic rather than by remembering which
    line comes first. Worth checking for before adding a guard -- an
    "impossible" case that cannot win does not need excluding.

    Returning 0 rather than a negative number is not a special case. `best`
    starts at 0 and only ever moves up, so a list of falling prices never
    improves on it -- the "do not trade" option is encoded as the initial value
    instead of as a branch.
    """
    cheapest = None
    best = 0
    for price in prices:
        if cheapest is not None and price - cheapest > best:
            best = price - cheapest
        if cheapest is None or price < cheapest:
            cheapest = price
    return best

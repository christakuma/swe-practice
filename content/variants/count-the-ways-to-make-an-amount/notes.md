# Same table, same additions, the loops the other way round

Revealed after grading. This is "Coin Change II" (LeetCode 518).

The fewest-coins problem and this one share a table — one entry per amount —
and that is exactly what makes the twist dangerous: the code you already have
is two edits away from an answer that is plausible and wrong.

```python
ways = [1] + [0] * amount
for coin in coins:
    for total in range(coin, amount + 1):
        ways[total] += ways[total - coin]
```

## The bug this exists to produce

```python
for total in range(1, amount + 1):
    for coin in coins:
        if coin <= total:
            ways[total] += ways[total - coin]
```

Amount outside, coin inside. For coins `[1, 2]` and an amount of 3 it returns
3: it has counted `1+2` and `2+1` as different. With the amount outermost,
*any* coin may be the last one added at every total, so every ordering of a
combination is built separately. That loop order is the right answer to a
different question — how many ordered sequences — which is the staircase
problem.

With the coin outermost, all the uses of the first coin are settled for every
total before the second coin exists. A combination can then only be assembled
in the order the coins are listed, so it is counted once.

## What the twist was testing

"Count the ways instead of finding the best" is a standard follow-up, and the
usual mistake is to keep the optimisation's shape and swap `min` for `+`.
Sometimes that is right. Here it silently changes what is being counted, and
the only defence is to work the smallest case that tells the two apart —
`[1, 2]` and 3 — by hand before trusting the table.

`ways[0] = 1` is the other thing to get right: there is one way to make
nothing, and every other entry is built on it.

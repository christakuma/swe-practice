# Greedy is wrong, and your pocket is why you think it is right

Take the largest coin that fits, repeat. On `[1, 5, 10, 25]` it is optimal for
every amount. On `[1, 3, 4]` making 6 it takes `4 + 1 + 1` — three coins — where
`3 + 3` is two.

The reason the mistake survives is that real currency systems are **designed**
so that greedy works. It is a property of the coin set (a "canonical" system),
not of the problem, and it is a deliberate design choice by mints so that
cashiers can make change without solving an optimisation problem. Test your
greedy implementation against pounds or dollars and it passes everything.

That is the general lesson, and it is worth more than the algorithm: **greedy
needs a proof, and "it worked on my examples" is not one.** When the examples
come from a domain that was designed to make greedy work, they are worse than no
examples.

## The table

```
best[0] = 0
best[a] = 1 + min(best[a - c] for c in coins if c <= a)
```

Every amount from 1 upwards, every coin at each one. O(amount × coins), and each
entry is final when computed because it only ever reads smaller amounts.

```
coins [1, 3, 4], amount 6

a     0  1  2  3  4  5  6
best  0  1  2  1  1  2  2
                  ^ 4 via one coin
                     ^ 4+1
                        ^ 3+3, beating 4+1+1
```

## Infinity rather than a sentinel

`math.inf` for "not reachable yet" means `best[a - c] + 1` stays arithmetically
true — infinity plus one is infinity, and `min` ignores it — so there is no
special case inside the loop. Only the final answer needs translating to `-1`.

With `-1` as the sentinel, every read has to be guarded, and the guard is easy
to omit on one branch. The bug then looks like an off-by-one rather than a
missing check.

## The other question with the same table

"How many **ways** are there to make the amount" looks like the same problem and
needs the loops in the other order:

```python
ways = [1] + [0] * amount
for coin in coins:            # coin outermost
    for target in range(coin, amount + 1):
        ways[target] += ways[target - coin]
```

Coin outermost counts **combinations** — `1+2` and `2+1` are one way. Target
outermost counts **permutations**. The fewest-coins version does not care,
because the minimum is the same either way, which is exactly why the loop order
looks arbitrary until you meet the counting variant and it is not.

## Recovering the coins themselves

The table holds counts, not choices. To report which coins, either store the
coin that achieved each entry and walk back from the target, or reconstruct by
testing which `best[a - c] + 1 == best[a]`. Same O(amount) space, and worth
knowing because "fewest coins" is rarely the question anyone actually has — they
want the coins.

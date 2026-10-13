# The loop order is the rule about reuse

Revealed after grading.

The two versions use the same table and differ only in how it is filled.

```python
# any number of each coin            # each coin once
for target in range(1, amount + 1):  for coin in coins:
    for coin in coins:                   for target in range(amount, coin - 1, -1):
        ...                                  ...
```

On the left, `best[target - coin]` is the answer for a smaller amount with
every coin still available, so a coin can be taken again and again. Nothing in
the table records which coins an entry used, and nothing needs to — reuse is
allowed.

On the right, the outer loop walks the purse. After the first `i` turns the
table describes what can be made **from the first `i` coins**. A coin is
offered once, in its own turn, and never again.

## Why downwards

Within one coin's turn, `best[target]` is updated from `best[target - coin]`,
a *smaller* index. Sweep upwards and that smaller entry has already been
updated in this same turn — it may already contain this coin, and you add it a
second time. Sweep downwards and every entry you read is still last turn's.

That one reversed `range` is the entire difference between the unbounded
knapsack and the 0/1 knapsack, and it is worth being able to derive rather
than recite. The two-dimensional table `best[i][target]` makes it obvious;
the one-dimensional version is that table with the rows overwritten in place,
and the sweep direction is what keeps the overwrite from reading its own
output.

## What the twist was testing

Whether "coins" meant denominations or objects. The standard prompt says
*each coin value may be used as many times as you like*; delete that sentence
and `[1, 5, 10]` making `3` goes from three coins to impossible. Duplicates
change meaning too: `[2, 2, 3]` is two denominations there and three coins
here, so deduplicating the input — harmless in the standard version — is a bug
in this one.

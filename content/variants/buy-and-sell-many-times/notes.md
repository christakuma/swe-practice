# Every rise is yours; every fall is someone else's

Revealed after grading. This is "Best Time to Buy and Sell Stock II"
(LeetCode 122).

The one-trade version is a search: find the best pair of days. Lifting the
limit turns it into something much simpler, and the interesting part is seeing
*why* it got simpler rather than harder.

```python
sum(max(later - earlier, 0) for earlier, later in pairwise(prices))
```

**A long trade is the sum of its days.** Buying at 1 and selling at 5 across
`[1, 2, 3, 5]` makes 4. So does buying and selling on each of the three days:
1 + 1 + 2. The intermediate prices cancel. That means there is never a reason
to *plan* a trade — any profitable stretch can be collected one day at a time,
and any day the price falls is a day you can simply not be holding.

## What the twist was testing

Whether you carry the old solution over. The one-trade answer tracks a running
minimum and the best spread above it, and it is tempting to extend that:
find the best trade, then the best trade in what is left. That is wrong
(`[1, 5, 3, 6]`: the best single trade is 1 to 6, which leaves nothing, for 5
against the available 7) and it is also far more machinery than the problem
needs.

When a constraint is *removed*, check whether the problem has become a
different, easier one before reaching for a generalisation of what you had.

## The state machine underneath

The general tool for this family is two running values: the most cash you can
have while holding a share, and while not. Every variation — a cooldown day, a
fee per trade, at most k trades — is a small edit to how those two update. The
sum of rises is what that machine collapses to when there are no extra rules.

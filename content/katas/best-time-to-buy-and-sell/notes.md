# Best Time to Buy and Sell — turn the question around

Revealed after grading. The problem is the classic one (LeetCode 121); the
wording above is ours. The useful move is not the algorithm, it is the
reframing that makes the algorithm obvious.

## The naive version, and what it is asking

```python
for buy in range(len(prices)):
    for sell in range(buy + 1, len(prices)):
        best = max(best, prices[sell] - prices[buy])
```

`O(n²)`. For each buy day it scans every later day looking for the highest
price. That is the wrong question to be asking repeatedly.

## The move

**Fix the sell day instead of the buy day.** "If I sell today, what is the best
I could have bought at?" has a one-number answer — the cheapest price so far —
and when you walk left to right you already have it.

```python
cheapest = None
best = 0
for price in prices:
    if cheapest is not None and price - cheapest > best:
        best = price - cheapest
    if cheapest is None or price < cheapest:
        cheapest = price
return best
```

`O(n)` time, `O(1)` space. Two running values, one pass, never looks backwards.

Same shape as Kadane's algorithm in
[maximum subarray](../maximum-subarray/notes.md): carry the best answer
*ending here* next to the best answer *anywhere*. Worth noticing that the two
problems are related more tightly than they look — the maximum profit over
`prices` is the maximum subarray sum over the daily *differences*.

## The ordering that turns out not to matter

The tempting rule is "record the profit before updating the minimum, or you
will let a day trade with itself". Half of that is right and the conclusion is
wrong, and the reason is the interesting part.

Update `cheapest` first and today *can* buy and sell from itself — but that
trade is worth `price - price`, exactly `0`, and `best` starts at `0` and only
ever moves up. **The illegal option is permitted and can never win, so both
orderings are correct.** Verified by brute force over every price list of
length up to seven: zero disagreements.

That is a better kind of safety than a convention. The constraint is enforced
by the arithmetic rather than by remembering which line comes first — and it is
worth checking for before adding a guard, because *an impossible case that
cannot win does not need excluding*. Guards that defend against harmless states
are how code acquires conditions nobody can later justify deleting.

## Why `best` starts at zero

"Do not trade" is always available and always worth 0. Making it the initial
value means a list of falling prices needs no special case — nothing ever
improves on it — and the empty list and the one-day list fall out for free.

Compare with seeding `best = float("-inf")` and clamping at the end, which
needs an extra branch and an extra concept. **Encoding the default answer as
the initial value of the accumulator is usually cleaner than detecting its
absence later.**

## The bug the tests are built around

```python
return max(prices) - min(prices)      # ignores the ordering constraint
```

It gets `[7, 1, 5, 3, 6, 4]` right, which is the worked example. It returns `9`
for `[10, 1]`, where the right answer is `0`, and `8` for `[5, 9, 1, 7]`, where
the right answer is `6`.

`test_agrees_with_a_brute_force_on_every_short_series` enumerates every list of
length ≤ 7 over five values — about a hundred thousand cases — against the
all-pairs search. The ordering constraint is what solutions get wrong, and it
only bites on particular arrangements of the maximum and minimum, so
enumerating beats choosing. Same approach as
[zero out rows and columns](../zero-out-rows-and-columns/notes.md): when the
input space is small enough to enumerate, enumerate it.

## What to take away

**When a nested loop recomputes the same summary, try fixing the other
variable.** Here the inner scan was looking for a maximum over a suffix; fixing
the sell day instead turned it into a minimum over a prefix, which is a running
value rather than a search.

That reframing — *iterate over the thing whose answer accumulates* — is the
same instinct behind prefix sums, Kadane's algorithm, and the running-minimum
trick in general. The algorithm is three lines once the question is the right
way round.

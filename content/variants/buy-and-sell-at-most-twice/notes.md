# Four pockets

Revealed after grading. This is "Best Time to Buy and Sell Stock III"
(LeetCode 123).

One trade needs one running value — the cheapest price so far. Unlimited
trades need none: take every rise. Two trades sit awkwardly between them, and
neither trick carries over.

## Why the obvious plan fails

*Take the best trade, then the best trade in whatever is left.* In
`1, 5, 2, 8` the best trade is `1 -> 8` for 7, and nothing is left. The answer
is 10, from `1 -> 5` and `2 -> 8`. The best single trade can be the two right
trades glued together, and once you have taken it you cannot have them.

## The state machine

Track the best amount of money you could be holding at each of four stages:

```python
first_buy = max(first_buy, -price)
first_sell = max(first_sell, first_buy + price)
second_buy = max(second_buy, first_sell - price)
second_sell = max(second_sell, second_buy + price)
```

Each line says "stay where you are, or arrive here today from the stage
before". The third line is the interesting one: the second share is bought
with the first trade's profit already in your pocket, which both chains the
trades in order and adds their profits.

"At most" comes for free. A trade made within a single day is worth zero, so
the one-trade answer and the no-trade answer are both among the candidates.

The other well-known solution is two passes: best single trade ending by each
day from the left, best starting from each day on the right, and the best sum
over the split point. Same `O(n)`, with `O(n)` memory, and it does not
generalise — the four lines above become a loop over `k` stages for
"at most k trades".

## What the twist was testing

Whether you reach for state when greed stops working. The one-trade solution
is greedy and feels like insight; the lesson of this version is that it was a
one-stage state machine all along.

# "No division" is a hint, not a restriction

The division solution is three lines and it is wrong:

```python
total = math.prod(numbers)
return [total // n for n in numbers]      # ZeroDivisionError waiting to happen
```

Work through `[1, 2, 0, 4]`. The total is 0, so every answer comes out 0 — and
the answer at the zero's own position should be 8. Guard against the zero and
you discover the real answer has three cases: no zeros (divide), one zero (every
position is 0 except the zero's own, which is the product of the rest), two or
more zeros (everything is 0). That is a correct solution and it is *more*
complicated than the one the constraint pushes you towards.

## The shape that generalises

The answer at `i` is everything left of `i` times everything right of `i`:

```
numbers:   1     2     3     4
left:      1     1     2     6        (running product, exclusive)
right:    24    12     4     1        (running product, exclusive)
answer:   24    12     8     6
```

Both rows are **prefix products** — the multiplicative version of a prefix sum —
and each is one pass. The two passes together are O(n), and because the second
one multiplies into the array you already built, there is no third array.

This is the same move as a prefix-sum array, and recognising it is what makes a
whole family of problems easy:

| question | built from |
|---|---|
| sum of any subrange, asked repeatedly | prefix sums |
| product of everything except one | prefix products, both directions |
| number of smaller elements to the left | prefix counts |
| maximum to the left of each position | prefix maxima |

The common structure: an answer about position `i` that depends on an aggregate
of one side, which can be accumulated once instead of recomputed per position.

## On the space claim

`O(1) extra space` here means "not counting the output", which is the standard
convention for this problem and worth being explicit about rather than letting
it be a gotcha. The output is n integers; you cannot return an answer without
it. What the claim excludes is the *second* n-sized array — the one you get by
building `left` and `right` separately and combining them. That version is
clearer on first write, and collapsing it is a two-line change.

## The edge cases that matter

- **one element** → `[1]`. The product of no elements is 1, the multiplicative
  identity, and a solution that special-cases it is usually a solution that
  initialised a running product to 0.
- **empty list** → `[]`. Falls out of the loop bounds; no special case needed.
- **negatives** → the sign takes care of itself. Nothing in the algorithm cares.

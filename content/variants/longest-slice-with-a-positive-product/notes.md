# Only the sign was ever needed

Revealed after grading. "Maximum Length of Subarray With Positive Product"
(LeetCode 1567).

## The same two-track idea

Maximum product keeps the largest *and* the smallest product ending at each
position, because a negative value swaps them. This keeps two lengths for
the same reason:

- `positive` — the longest slice ending here whose product is positive;
- `negative` — the longest ending here whose product is negative.

```python
if value == 0:
    positive = negative = 0
elif value > 0:
    positive += 1
    negative = negative + 1 if negative else 0
else:
    positive, negative = (negative + 1 if negative else 0), positive + 1
```

## The catch

Zero is doing double duty: it is a length, and it means "there is no such
slice". Extending a slice that does not exist must not produce one.

- After `[1, 2]` there is no negative-product slice. A third positive value
  does not create one, so `negative` stays 0 — not 1.
- A negative value *can* start a negative slice by itself, so `positive + 1`
  is right even when `positive` is 0.

Write `negative += 1` unconditionally and `[1, 2, -3]` answers 3: the code
believes it has a negative slice of length two to cancel against the -3.

## The swap

The negative branch must use the *old* values of both:

```python
positive, negative = (negative + 1 if negative else 0), positive + 1
```

On two lines, the second reads a `positive` that the first has already
overwritten.

## The other way to see it

Split the list at zeros. Within a zero-free stretch, the product is positive
if the number of negatives is even. If it is odd, drop the shortest prefix
that contains the first negative, or the shortest suffix that contains the
last — whichever leaves more.

That is just as fast and arguably easier to believe. The two-length version
is the one that generalises: it is the same shape as the maximum-product
solution, which is why an interviewer asks them together.

## What the twist was testing

Noticing what the answer actually depends on. The values here are near a
thousand million and there are a hundred thousand of them; the product of
the lot has close to a million digits and nobody wants it. The question
only ever asked about the sign, and a sign is one bit. Carrying less than
the problem appears to hand you is often the whole trick.

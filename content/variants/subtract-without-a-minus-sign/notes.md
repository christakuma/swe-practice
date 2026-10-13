# Subtraction is addition you have not recognised yet

Revealed after grading. The follow-up to "Sum of Two Integers" (LeetCode 371).

There is no new circuit to design. In two's complement, `-b` is `~b + 1`, so:

```python
subtract(a, b) == add(a, add(~b, 1))
```

and the adder built from XOR and carries is used twice.

The edge worth understanding is `b = INT_MIN`. Its negation does not exist in
32 bits — `~INT_MIN + 1` wraps back round to `INT_MIN` itself. The arithmetic
still comes out right, because everything is done modulo `2**32`:
`subtract(0, INT_MIN)` is `INT_MIN`, which is the wrapped value of `2**31`.

That is the reason two's complement won. One adder does addition and
subtraction, signed and unsigned, with no special cases — the representation
was chosen so that this follow-up question would have a one-line answer.

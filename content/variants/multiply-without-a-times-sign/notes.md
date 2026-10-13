# Long multiplication, with the adder you already built

Revealed after grading.

A product is a sum of rows, and in binary a row is as simple as a row can be:
the digit of `b` is 0 or 1, so the row is either nothing or `a` shifted left.

```python
word = 0
while b:
    if b & 1:
        word = _add(word, a)
    a = (a << 1) & MASK
    b >>= 1
```

`_add` is the standard problem's loop — XOR for the sum without carries, AND
shifted left for the carries, repeat until there are none. So this is at most
thirty-two additions of at most thirty-two rounds, whatever the operands are.

## Why there is no code for the sign

The tempting plan is to strip the signs, multiply the magnitudes and put the
sign back. It works until `INT_MIN`, whose magnitude is not a 32-bit signed
number, and it is not needed.

Two's complement is arithmetic modulo `2**32`. The low 32 bits of a product
depend only on the low 32 bits of the factors — the same reason the last digit
of a decimal product depends only on the last digits. Mask both operands,
multiply the *patterns* as unsigned numbers, keep 32 bits, and the pattern that
comes out is the right one whatever the signs were. `-1` is `0xFFFFFFFF`;
`0xFFFFFFFF` times `0xFFFFFFFF` ends in `0x00000001`.

## What the twist was testing

Whether the adder was understood well enough to be *used*. The standard
problem can be passed by remembering five lines. This one needs those lines as
a subroutine, needs `b` masked before the loop so that a negative multiplier
ever reaches zero, and needs `a` masked as it shifts so the rows stay inside
the word.

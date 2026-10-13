# Two shifts and a mask

Revealed after grading. Bit rotation — `rol` in assembly, `rotl` in C++20,
`Integer.rotateLeft` in Java. Python has no built-in for it, because Python
integers have no width to rotate within.

```python
k %= 32
return ((n << k) | (n >> (32 - k))) & 0xFFFFFFFF
```

## Why two shifts

A rotation by `k` splits the word into the top `k` bits and the low
`32 - k`, and swaps the two pieces:

```
[ top k ][      low 32-k      ]
[      low 32-k      ][ top k ]
```

- `n << k` puts the low piece in its new place — and pushes the top piece
  out past bit 31.
- `n >> (32 - k)` puts the top piece at the bottom — and drops the low piece
  off the end.

Each shift places one piece correctly. OR them.

## The mask is the width

In C, a 32-bit left shift discards what goes past the top. In Python it does
not: `0xF0000000 << 4` is `0xF00000000`, a 36-bit number. The mask is what
removes it.

This is the reversal problem's lesson again. A fixed width in Python is
something you maintain by hand, and every operation that can grow the value
needs a mask after it.

## `k % 32`

Rotating by the width is the identity, so only the remainder matters. That
turns a `k` of a thousand million into a `k` of zero, and keeps `32 - k`
from going negative — Python raises `ValueError` on a negative shift count.

## `k = 0`

Then the right shift is by 32, which empties a 32-bit value, and the answer
is `n`. Nothing special needed.

That is luck of the language. In C and C++, shifting a 32-bit value by 32 is
undefined behaviour, and on x86 it typically shifts by 0 instead and gives
the wrong answer. The portable idiom there is

```c
(n << k) | (n >> (-k & 31))
```

Worth knowing if the interviewer's next question is "and in C?".

## What the twist was testing

Whether "the word is 32 bits wide" stuck as an idea or only as a loop bound.
Reversal can be done with a loop that happens to run 32 times. Rotation has
no loop; the width appears as a modulus, a shift amount and a mask, and all
three have to agree.

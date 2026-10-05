# Reverse the Bits of a Word — the width is not in the language

Revealed after grading. The problem is the classic one (LeetCode 190); the
wording above is ours. The bit shuffling is three lines. The reason it is worth
doing in Python is that the problem has a parameter the language refuses to
supply, and getting that wrong is the only way to fail it.

## The move

Read the lowest bit of the input; push it onto the **high** end of the result:

```python
result = 0
for _ in range(WORD_BITS):
    result = (result << 1) | (n & 1)
    n >>= 1
return result
```

Shifting `result` left *before* each write is what does the reversing. The
result grows from the bottom up, so the first bit read gets pushed left by the
thirty-one shifts that follow it, and the last bit read lands at position zero.
No index arithmetic, no `31 - i` to get wrong.

`O(1)` time — thirty-two steps regardless of the input — and `O(1)` space.

## The actual difficulty

```python
while n:                      # wrong
    result = (result << 1) | (n & 1)
    n >>= 1
```

This passes `0` and `4294967295` and fails `1`, returning `1` instead of
`2**31`.

The reason is worth sitting with. **A 32-bit word's leading zeros are part of
the word**, and reversing moves them into the low positions — so they have to
be shifted through just like the ones. `while n` stops when the *input* runs
out, which skips exactly as many shifts as there were leading zeros.

In C this bug is hard to write, because `uint32_t` carries the width with the
value. In Python the width is nowhere: `0b1` is an integer, not a word, and
`1 << 1000` is as valid as `1 << 3`. The only place "32" exists is the problem
statement, which is why the stub names it `WORD_BITS` instead of burying a
literal in a range — the magic number *is* the specification.

This is the general shape of the trap, and it is not confined to this kata:
**when you port a fixed-width algorithm to Python, every width assumption
becomes an explicit obligation.** Masking with `& 0xFFFFFFFF`, bounding a loop
at 32, treating the high bit as a sign — all of it was free in C and is yours
to remember here. [Add without a plus sign](../add-without-a-plus-sign/notes.md)
is the same lesson with sharper teeth, because there the missing overflow is
what the algorithm *depends on*.

## The tests worth reading

Two of them are doing real work.

`test_is_its_own_inverse` leans on reversal being an **involution**: reverse
twice and you are back where you started. That is a property rather than a
table of expected values, so it holds for any input and does not need a
reference implementation to state. A width error does not cancel under
composition, so it fails here loudly.

`test_agrees_with_a_string_reversal_across_a_dense_range` checks all 2048 small
values against `format(v, '032b')[::-1]` — the banned one-liner, used as an
**independent oracle**. Writing the forbidden solution inside the test suite is
good practice, not cheating: it is a second implementation with completely
different failure modes, and small values are precisely where the leading-zero
bug lives.

## The faster versions you would actually ship

Byte-table lookup: precompute the reversal of all 256 bytes, then reassemble
four of them. Four lookups and three shifts, no loop.

Or the divide-and-conquer swap, which reverses in `log 32 = 5` steps by
swapping progressively larger blocks:

```python
n = ((n & 0x55555555) << 1)  | ((n >> 1)  & 0x55555555)   # adjacent bits
n = ((n & 0x33333333) << 2)  | ((n >> 2)  & 0x33333333)   # pairs
n = ((n & 0x0F0F0F0F) << 4)  | ((n >> 4)  & 0x0F0F0F0F)   # nibbles
n = ((n & 0x00FF00FF) << 8)  | ((n >> 8)  & 0x00FF00FF)   # bytes
return ((n & 0x0000FFFF) << 16) | ((n >> 16) & 0x0000FFFF) # halves
```

Both are `O(1)` like the simple loop, with a better constant. Neither is worth
reaching for first, and the masks are where the width assumption becomes
undeniable — every constant in that block is 32 bits wide by construction.

## What to take away

The bit mechanics are routine. The transferable part is that **an algorithm can
have a parameter the type system used to carry for you.** When you find
yourself writing `while n` for a problem posed over a fixed-width word, the
loop bound is the specification and the data cannot tell you it.

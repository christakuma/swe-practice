# Count the Set Bits — what subtracting one does

Revealed after grading. The problem is the classic one (LeetCode 191); the
wording above is ours. In production you write `n.bit_count()` and move on.
It is here because the identity behind the fast version is one of the three or
four bit tricks that actually recur, and because it is the clearest example of
a loop whose cost depends on the *data* rather than the word size.

## The honest first version

```python
total = 0
while n:
    total += n & 1
    n >>= 1
return total
```

`n & 1` reads the lowest bit; `n >> 1` drops it. Correct, `O(bits)`, and it
visits every zero on the way. For `2**60` that is sixty-one iterations to find
a single 1.

## The move

Look at what subtracting one does in binary:

```
n      = 1011 0100
n - 1  = 1011 0011
```

The borrow propagates through the trailing zeros: the **lowest set bit flips to
0**, and every 0 below it becomes 1. Above that bit, nothing changes. So `n`
and `n - 1` agree strictly above the lowest set bit and disagree from it down,
which means:

```
n & (n - 1) = 1011 0000      # n with its lowest set bit cleared
```

Count how many times you can do that before reaching zero:

```python
total = 0
while n:
    n &= n - 1
    total += 1
return total
```

Now the loop runs once per **set** bit. `O(s)` for `s` bits set — one iteration
for `2**60`, and on a sparse integer of any width that is the entire cost.

## The family this belongs to

The same identity answers several questions, which is the reason to own it
rather than memorise this one function:

- **Is `n` a power of two?** Exactly one bit set, so `n > 0 and n & (n - 1) == 0`.
- **Clear the lowest set bit:** `n & (n - 1)`.
- **Isolate the lowest set bit:** `n & -n`. Two's complement negation is
  `~n + 1`, which inverts everything above the lowest set bit and leaves that
  bit alone — so the AND keeps precisely it. This is how a Fenwick tree walks
  its indices.
- **Fill below the lowest set bit:** `n ^ (n - 1)`.

## The Python-specific trap

Python integers have **no width**. `1 << 1000` is an ordinary int, and there is
no sign bit to run out of. That makes two habits from C wrong here:

```python
for i in range(32):          # silently truncates anything wider
    total += (n >> i) & 1
```

`test_counts_bits_above_the_32_bit_boundary` exists for exactly that solution,
which passes every small case first. The `while n:` form has no width baked in
and needs no bound.

It also means `~n` is **not** a bit-flip within a fixed word — `~5 == -6`, not
`250`. Any algorithm that relies on complementing within a width has to mask
explicitly: `~n & 0xFF`. That comes up properly in
[add without a plus sign](../add-without-a-plus-sign/notes.md), where the
absence of overflow is the whole difficulty.

## What this kata cannot test

The complexity claim. A bit-by-bit loop over `1 << 1000` does a thousand
iterations, which is microseconds — so no wall-clock limit can distinguish it
from the Kernighan version at any input size that fits in a test. The declared
`O(s)` is a claim you make and defend, not one the grader checks (PLAN.md §7).
The tests here are about *correctness* at widths that break fixed-word
assumptions, which is the part that can be checked.

## What to take away

**The loop that costs what the data costs, not what the container allows.**
Iterating over 64 bit positions to find one set bit is the same shape of waste
as scanning a list to answer a membership question — you are paying for the
representation instead of the information. Clearing the lowest set bit is the
cheapest possible fix, and it falls straight out of knowing what a borrow does.

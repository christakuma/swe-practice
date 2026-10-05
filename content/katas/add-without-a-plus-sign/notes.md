# Add Without a Plus Sign — the overflow you have to build

Revealed after grading. The problem is the classic one (LeetCode 371); the
wording above is ours. The bit identity at its centre is two lines and genuinely
beautiful. Everything hard about it in Python comes from a feature: integers
that never overflow.

## The move

Add two single bits and look at what comes out:

```
0 + 0 = 00        low bit = 0,  carry = 0
0 + 1 = 01        low bit = 1,  carry = 0
1 + 0 = 01        low bit = 1,  carry = 0
1 + 1 = 10        low bit = 0,  carry = 1
```

The low bit is `a ^ b`. The carry is `a & b`. And both generalise to whole
words at once, in parallel, with no loop over positions:

- **`a ^ b`** is the sum of `a` and `b` with every carry thrown away.
- **`(a & b) << 1`** is exactly the carries that were thrown away, already
  shifted into the column they belong in.

So addition is: compute those two, then add *them* together. Which is the same
problem again — so repeat until there are no carries left:

```python
while b:
    carry = (a & b) << 1
    a = a ^ b
    b = carry
return a
```

It terminates because each round moves every remaining carry strictly one place
left. After at most 32 rounds, nothing is left inside the word.

That is a complete and correct 32-bit adder, and it is also the hardware one:
this loop is a ripple-carry adder, one round per gate delay.

## Why that code hangs in Python

Run it with `a = -1`. It never returns.

In C the carries fall off the end of a 32-bit register and vanish, and that
disappearance is doing two jobs: it is what makes the loop finish, and it is
what makes overflow wrap. Python integers are unbounded, so **nothing falls
off**. A carry out of bit 31 just makes the number wider. And Python's `-1` is
conceptually `...1111111`, with no end — so there is always another carry and
`b` never reaches zero.

The fix is to impose the word the algorithm assumes:

```python
a &= MASK
b &= MASK
while b:
    carry = (a & b) << 1
    a = (a ^ b) & MASK
    b = carry & MASK
```

`& MASK` is not defensive tidying. It is the 32-bit register, written out by
hand because the language does not have one.

## Reinterpreting the pattern at the end

After the loop, `a` holds 32 bits. Those bits are a *pattern*, not a Python
number, and if the top one is set the pattern means something negative — which
Python will not conclude on its own. `0xFFFFFFFF` is 4294967295 to Python and
−1 to a 32-bit machine.

```python
return a if a <= INT_MAX else ~(a ^ MASK)
```

`a ^ MASK` flips every bit inside the word; `~` of that is the negative integer
with those two's complement bits. Check it on `0xFFFFFFFF`: `^ MASK` gives 0,
`~0` is −1. On `0xFFFFFFFE`: `^ MASK` gives 1, `~1` is −2.

The usual spelling is `a - WORD`, which is banned here — and being forced into
`~(a ^ MASK)` is a small gift, because it makes you state the two's complement
identity explicitly instead of letting subtraction imply it.

## The two halves of the lesson

**Half one: the identity.** `sum = a ^ b`, `carry = (a & b) << 1`, iterate.
Worth knowing because it is what an adder *is*, and because the same
decomposition shows up in carry-save adders and in counting bits across
parallel lanes.

**Half two, and the one that generalises further: a fixed-width algorithm
ported to Python has obligations the type system used to discharge.** Here the
missing overflow is not an inconvenience around the edges — the algorithm's
*termination* depended on it. That is a stronger version of the trap in
[reverse the bits of a word](../reverse-the-bits-of-a-word/notes.md), where the
missing width only produced a wrong answer.

When you port something from C and it hangs rather than misbehaving, look for
the place where the original was relying on a value running out of room.

## On the tests

Two of them carry the weight. `test_agrees_with_a_reference_across_every_small_pair`
checks all 58,081 pairs in −120..120 against `(a + b)` wrapped — the banned
operator, used deliberately as an **independent oracle**. Sign-handling
special-cases (`if a < 0: ...`) routinely pass a dozen hand-picked cases and
die somewhere in a bulk sweep like that.

The other is `test_wraps_on_positive_overflow`. `add(INT_MAX, 1) == INT_MIN` is
not a curiosity — it is the specification. A solution that returns 2147483648
has not implemented 32-bit addition, it has implemented Python addition with
extra steps.

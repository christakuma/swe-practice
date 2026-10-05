# Is It an Anagram — the question is about counts

Revealed after grading. The problem is the classic one (LeetCode 242); the
wording above is ours. It is short, and the thing worth taking from it is that
two of the three obvious solutions answer a *different question* than the one
asked.

## Three solutions, three questions

```python
sorted(a) == sorted(b)        # "do these have the same sorted order?"
set(a) == set(b)              # "do these use the same characters?"
Counter(a) == Counter(b)      # "do these have the same character counts?"
```

Only the third is the question. The first is **stronger** than needed — it
imposes a total order on characters to answer a question that has nothing to do
with ordering, and pays `O(n log n)` for it. The second is **weaker** — it
throws away multiplicity, so `"aab"` and `"abb"` look identical.

`test_respects_multiplicities` exists for the set version, which is the more
dangerous of the two because it is wrong rather than merely wasteful.

## The move

An anagram is a claim about multiplicities, so build the tally:

```python
if len(first) != len(second):
    return False
counts = {}
for character in first:
    counts[character] = counts.get(character, 0) + 1
for character in second:
    remaining = counts.get(character, 0)
    if remaining == 0:
        return False
    counts[character] = remaining - 1
return True
```

`O(n)` time, `O(k)` space for `k` distinct characters. One dict, not two: count
up for the first string and down for the second, and a match leaves every entry
at zero.

## The length check is load-bearing

This is the part worth being careful about, because it looks like a cheap
early exit and it is doing real work.

The count-down loop can only detect a character that occurs **too often** in
`second`. It never inspects what is left over in the tally. So without the
length check:

```python
is_anagram("ab", "a")   # True — the `b` is still outstanding, unexamined
```

Every proper prefix of an anagram passes. Equal lengths close the gap exactly:
if the totals match and nothing in `second` ran out of budget, nothing can be
left over.

So the `O(1)` guard is what **licenses the single tally**. Drop it and you need
a third loop checking every count is zero. `test_rejects_a_proper_prefix` is
the case, and it was found by running the version without the check rather than
by reasoning about it.

**The general shape: an early return that also simplifies the body is not an
optimisation, it is part of the algorithm.** Worth distinguishing from the kind
you can delete freely.

## Why not a fixed array of 26

```python
counts = [0] * 26
counts[ord(c) - ord('a')] += 1
```

Faster, `O(1)` space, and it assumes the alphabet. The prompt says every
character counts — spaces, punctuation, case — and
`test_handles_non_ascii_characters` uses `"café"` and `"日本語"`, where this
either raises `IndexError` or corrupts a neighbouring slot.

It is the right answer when the input is genuinely constrained to lowercase
ASCII and the constraint is written down. It is a very common way to ship a
bug when the constraint was assumed. Python's `str` iterates code points, so a
dict costs you nothing to be correct about.

## What to ship

`Counter(a) == Counter(b)`. It is one line, it is exactly the right question,
and it is `O(n)`.

The loop is written out here because the point of the kata is knowing what that
comparison *costs* — `O(n)` time, `O(k)` space, two hash tables built and then
compared — rather than treating it as free. Reaching for `Counter` because you
know what it does is different from reaching for it because it is short.

## What to take away

**Match the strength of your tool to the strength of the question.** Sorting
answers "same order", sets answer "same membership", counters answer "same
multiset". Reaching for a sort when you need a multiset comparison is the same
category of mistake as reaching for a sort when you need a minimum — it works,
and it tells you that you have not identified what you were asked.

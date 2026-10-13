# The first mismatch names two suspects

Revealed after grading. This is "Valid Palindrome II" (LeetCode 680).

Allowing one deletion sounds like it multiplies the work by `n`: try removing
each character and check what is left. It does not, and seeing why is the
exercise.

## Where the deletion has to be

Walk in from both ends. While the two characters agree, they are a matched
pair, and deleting either one would break a pair that works. So the deletion
— if one is needed — is not among them.

At the **first** pair that disagrees, one of those two characters must go.
That is two candidates, wherever in the string you are:

```python
if text[low] != text[high]:
    return mirrors(low + 1, high) or mirrors(low, high - 1)
```

Each check is an ordinary palindrome scan of the part still between the
pointers. One pass to find the mismatch, at most two more to settle it.

## Try both

`"abbca"` is fixed only by deleting from the right; `"acbba"` only from the
left. Peeking one character ahead to guess which side is "the odd one out"
works on most inputs and fails on strings where both sides look plausible.
`or` costs nothing and is always right.

## What the twist was testing

Two things changed and only one was announced loudly. The deletion is the
headline. The quiet one is that **nothing is ignored any more**: no case
folding, no skipping punctuation. Carrying the standard version's
`isalnum()` filter across is the commonest way to fail this in practice —
the code is right for a problem that is no longer the one being asked.

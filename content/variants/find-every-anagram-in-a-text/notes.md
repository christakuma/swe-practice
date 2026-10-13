# A window that remembers

Revealed after grading. This is "Find All Anagrams in a String" (LeetCode 438).

One window is the standard problem: equal character counts. The point of this
version is that neighbouring windows share all but two characters, so nothing
should be recounted.

```python
shift(character, 1)                 # one enters
if end >= width:
    shift(text[end - width], -1)    # one leaves
```

**One integer instead of a dict comparison.** Comparing two count dicts at
every position costs the size of the alphabet each time. Tracking how many
characters are currently out of balance makes the test `unsettled == 0`,
which is constant whatever the alphabet.

The same shape solves "does the text contain a permutation of the pattern"
and, with a slightly different condition, the smallest window covering a set
of characters. Fixed-width window, counts, and a single number that says
whether the window is good.

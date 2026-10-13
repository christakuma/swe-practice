# Forward to find an end, backward to find the start

Revealed after grading. "Minimum Window Subsequence" (LeetCode 727).

## Why the old window fails

The covering window keeps a tally: how many of each character are inside.
A tally cannot see order. `"cab"` and `"abc"` have the same tally. So the
whole mechanism — grow until the counts are satisfied, shrink while they
stay satisfied — has nothing to hold on to.

## Two greedy walks

**Forward.** From `scan`, match the pattern left to right, taking each
character the first time it appears. When the last one matches at `end`,
that is the earliest any window starting at or after `scan` can finish.

**Backward.** From `end`, match the pattern right to left, again taking
each character the first time it appears going back. Where that stops is
the *latest* a window ending at `end` can start.

```
text      a  x  x  b  a  b        pattern  a b
forward   a . . . b               end = 3
backward  a . . . b               start = 0      "axxb"
resume from start + 1 = 1
forward         . . . a b         end = 5
backward              a b         start = 4      "ab"
```

Earliest end, then latest start: nothing ending there is shorter.

## Resume after the start, not the end

After a window `start..end`, the scan resumes at `start + 1`.

Resuming at `end + 1` feels natural — that text has been "used" — and is
wrong, because windows overlap:

```
a x a a        pattern  a a
first window:  a x a          (0..2)
the answer:        a a        (2..3) -- begins inside the first
```

## Ties

Windows are found in order of where they start. Replace the best only when
the new one is **strictly** shorter, and the earliest of the shortest is
what remains.

## The tempting one-liner

```python
re.search("a.*?b.*?c", text)
```

A lazy regular expression finds the *leftmost* match and makes it as short
as it can from there. Leftmost is not shortest: on `"axxbab"` it returns
`"axxb"`.

## The other standard answer

Dynamic programming: for each position in the text and each prefix of the
pattern, the latest start of a window that ends here and holds that prefix.
`O(n * m)` always, and no argument about greediness needed. The two-walk
version is the same bound in bad cases and far less work in ordinary ones.

## What the twist was testing

Seeing that a tool has stopped applying, and why. "Covering" and
"containing as a subsequence" sound like the same problem with a stricter
condition, and the first instinct is to add an order check to the counting
window. The condition is not one a count can express. What replaces it is
still two pointers and still a window — but found by walking, not by
tallying.

# Read ahead, write behind

Revealed after grading. This is "Remove Duplicates from Sorted Array"
(LeetCode 26).

Moving zeroes taught a shape: one index reads every element, a second index
trails behind and marks where the next *kept* element goes.

```python
write = 0
for value in numbers:
    if keep(value):
        numbers[write] = value
        write += 1
```

Everything before `write` is finished output; everything from the read
position on is unread input; the gap between them is rubbish. `write` can
never overtake the reader, so nothing is lost.

That skeleton is the whole family. Only `keep` changes:

- move zeroes: `value != 0`
- remove a given value: `value != target`
- **remove repeats from a sorted list: `value != numbers[write - 1]`**
- allow each value at most twice: `value != numbers[write - 2]`

## Why compare with the last value written

In a sorted list, equal values are adjacent, so "new" means "different from
the one before". But *which* one before? The previous element read has
possibly been overwritten — the list is changing under the scan. The last
value **written** is always intact and is, by construction, the most recent
distinct value. Comparing against the output rather than the input is what
makes the at-most-twice version a one-character change.

## The contract

Returning a count and leaving junk past it feels odd in Python, where
`numbers[:] = sorted(set(numbers))` is right there. It is the contract of
every language without resizable arrays, and of every buffer API: *here is
how much of it is valid*. The junk is not a bug to tidy up.

## What the twist was testing

Whether the two-pointer compaction was learned as a pattern or as "the zeros
one". Same loop, same invariant, different predicate — and one new thing,
which is that the predicate looks at the output being built.

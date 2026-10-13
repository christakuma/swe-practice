# From "is there a way" to "how many ways"

Revealed after grading. The counting form of "Word Break" (LeetCode 139); its
harder sibling, which lists the sentences, is LeetCode 140.

The table has the same shape: one entry per prefix of the string. The entry's
type changes from a boolean to an integer, and two small things change with
it.

```python
ways = [1] + [0] * len(text)        # one way to split nothing
...
ways[end] += ways[end - length]     # add, do not stop
```

**The base case is 1, not True.** It reads the same and means something
different: there is exactly one way to split the empty string, and every
other count is built by adding copies of it.

**No early exit.** The yes-or-no version can `break` as soon as one word
works. A count has to consider every word that ends at this position.

**Deduplicate the dictionary.** Two copies of a word are one word. Looping
over the list rather than a set quietly doubles every split that uses it.

Turning a decision into a count is usually this mechanical: `or` becomes `+`,
`True` becomes `1`, and every shortcut that relied on "one is enough" has to
go.

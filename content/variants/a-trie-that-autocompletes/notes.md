# The second half of `starts_with`

Revealed after grading. This is the core of "Search Suggestions System"
(LeetCode 1268) and of every search box.

`starts_with` walks down the trie along the prefix and reports whether it
arrived. The node it arrives at is the interesting thing: **every word stored
at or below it is a completion, and nothing else is.** The standard problem
throws that node away after glancing at it.

## Listing in order

A depth-first walk from that node visits every completion. Two rules make the
visiting order ascending:

- take each node's children in sorted order;
- report a node's own word **before** its children. `"car"` sorts before
  `"card"`, and in the trie `"card"` is below `"car"`.

That is a pre-order traversal. Breadth-first gets the second rule right and
the first wrong — it lists by length, putting `"b"` before `"abc"`.

## Stopping

```python
while stack and len(found) < limit:
```

The limit belongs in the loop condition. Collecting every match and slicing
is the same answer and misses the point of the structure: with fifty thousand
words under a one-letter prefix and three suggestions wanted, the walk should
touch about a dozen nodes.

Recursive versions need care here. A helper that appends to a shared list has
to check the limit before recursing into each child, or it carries on through
the whole subtree after the list is full.

## The alternative worth knowing

Keep the words in a sorted list and binary-search for the prefix; the
completions are the next `limit` entries that still start with it. Lookups
are just as fast and the code is three lines. Insertion is `O(n)`, though,
which is the trade: the trie is for a dictionary that keeps changing.

## What the twist was testing

That a trie was understood as a tree you can *walk*, not only a tree you can
*probe*. `contains` and `starts_with` both follow one path and stop. Most of
what tries are actually used for — completion, counting, longest match —
starts where those stop.

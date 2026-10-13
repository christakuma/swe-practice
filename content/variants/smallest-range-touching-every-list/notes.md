# The heap was a window all along

Revealed after grading. "Smallest Range Covering Elements from K Lists"
(LeetCode 632).

## What the merge was holding

A k-way merge keeps a heap with one node from each list — each list's
current front. The standard problem only ever looks at the top of it.

Look at the whole heap instead. It is **one value from every list**. So

```
(smallest value in the heap, largest value in the heap)
```

is a range that touches every list. More than that: it is the *narrowest*
range whose low end is that smallest value, because every other list is
represented by its smallest value that has not been passed yet.

## The walk

```python
while True:
    lowest, index, node = heap[0]
    if highest - lowest < best[1] - best[0]:
        best = (lowest, highest)
    if node.next is None:
        return best
    following = node.next
    highest = max(highest, following.value)
    heapq.heapreplace(heap, (following.value, index, following))
```

Pop the smallest, push its successor: the same move as the merge. Each step
tries the next low end in ascending order. The answer is the narrowest range
seen.

- **`highest`** is not something a min-heap can give you. Track it by hand.
  It only changes on a push, and only upwards — nothing larger than it ever
  leaves, because only the smallest leaves.
- **Why advance the smallest?** Moving any other list forward keeps the low
  end where it is and can only raise the high end. The smallest is the only
  one whose replacement might narrow the range.
- **When to stop.** When the list holding the smallest has no more nodes.
  Every range after that would start above its last value and miss it.
  Carrying on with the other lists is the classic wrong turn; it finds
  narrower ranges that are not answers.
- **Ties.** A strict `<` keeps the first range of a given width, and ranges
  are met in ascending order of low end.

## The other standard answer

Tag every value with the list it came from, sort them all together, and
slide a window that must contain every tag at least once — "Smallest Window
Covering" with list numbers for characters. `O(n log n)` instead of
`O(n log k)`, and easier to get right.

The two are the same idea. The heap version is that sliding window, with
the sort done lazily by a merge.

## What the twist was testing

Whether you understand the data structure you built or only the result it
produced. The merge's heap is a moving cross-section through all k lists,
and "one from each list, as close together as possible" is a question about
cross-sections. Nothing is merged here and nothing new is built — the
follow-up is answered by looking at more of what was already there.

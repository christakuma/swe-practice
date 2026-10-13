# Compare with the tail, and cut the tail

Revealed after grading. "Merge k Sorted Lists" (LeetCode 23) combined with
"Remove Duplicates from Sorted List" (LeetCode 83).

The heap delivers nodes in ascending order, so duplicates arrive together and
one comparison is enough:

```python
if tail is dummy or tail.value != value:
    tail.next = node
    tail = node
```

Two things go wrong when the two problems are combined.

**Skipping a node must not skip its list.** The successor is pushed whether
or not the node itself is kept. Putting the push inside the `if` drops the
rest of any list whose front was a duplicate.

**`tail.next = None`.** In the standard merge every node is linked to the next
one taken, so the list ends properly on its own. Here the last node kept may
still point at a duplicate that was skipped — `[1, 5, 5]` leaves the first 5
pointing at the second. Reusing nodes means inheriting their old links.

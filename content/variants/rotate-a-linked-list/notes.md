# Close the ring, then choose where to cut it

Revealed after grading. This is "Rotate List" (LeetCode 61).

Removing the nth node from the end is a problem about *finding* a place
without knowing the length. This one looks like it wants the same trick, and
is quietly different: `k` can be bigger than the list, so there is no
avoiding the length.

Once you accept one walk to the tail, something nicer is available. Join the
tail to the head:

```
1 -> 2 -> 3 -> 4 -> 5 -+
^----------------------+
```

A ring has no first node. Every rotation of the list is this same ring,
opened at a different place. So "rotate by k" is:

```python
tail.next_node = head                      # close it
for _ in range(length - k % length):       # walk to the new tail
    tail = tail.next_node
new_head = tail.next_node
tail.next_node = None                      # open it
```

## The details

- **`k % length`.** Rotating by the length is a full turn. A `k` of a
  thousand million on a seven-node list is a rotation by six.
- **`k % length == 0`.** The loop walks `length` steps, all the way round to
  the old tail, and the cut lands where the list was open before. No special
  case — which is the main thing closing the ring buys.
- **Empty list.** `k % 0` is a `ZeroDivisionError`. Check first.
- **Direction.** Rotating *right* by `k` cuts `length - k` nodes from the
  front, not `k`.

## What the twist was testing

Reading "`k` may be larger than the list" as a statement about the structure
of the problem rather than as an edge case to patch. Position `k` and
position `k + length` are the same place, which means the natural home for
this problem is a circle — and once the list is a circle, the rotation has
already happened.

# Two chains, leapfrogging

Revealed after grading. This is "Odd Even Linked List" (LeetCode 328).

The standard reorder needed three techniques — find the middle, reverse the
back half, interleave. This one needs a single walk, and the trick is to stop
thinking of it as rearranging one list and start thinking of it as unpicking
it into two.

```python
odd.next = even.next
odd = odd.next
even.next = odd.next
even = even.next
```

Each node's new successor is the node two places on, so the odd and even
chains step past each other down the list. At the end, the odd tail is joined
to the first even node, which is why `even_head` was saved before anything
moved.

**Position, not value.** The name invites the mistake. `[2, 1, 3, 5, 6, 4]`
groups as positions 1, 3, 5 and then 2, 4, 6, whatever numbers those nodes
hold.

# Push to the front

Revealed after grading. A classic follow-up to "Merge Two Sorted Lists"
(LeetCode 21).

The merge is unchanged — take the smaller front node each time. Only where
the node is *put* changes:

```python
taken.next = head
head = taken
```

Appending to the tail builds the list in the order nodes are taken. Pushing
onto the head builds it in reverse. Taking smallest-first and pushing to the
front therefore yields largest-first, in one pass, with no dummy node and no
tail pointer.

Merging normally and then reversing is correct and twice the pointer work.
The point of the follow-up is noticing that "reverse" and "build by head
insertion" are the same thing.

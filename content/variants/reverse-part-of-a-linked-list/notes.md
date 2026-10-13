# A fixed anchor, and one node moved at a time

Revealed after grading. This is "Reverse Linked List II" (LeetCode 92).

Reversing a whole list has two loose ends: the old head becomes the tail, the
old tail becomes the head. Reversing a stretch in the middle has four, and
most of the difficulty is keeping them straight. The cleanest way is not to
detach the stretch at all.

```python
dummy = ListNode(0, head)
before = dummy
for _ in range(left - 1):
    before = before.next          # the node just ahead of the range
tail = before.next                # first node of the range; will end last
for _ in range(right - left):
    moving = tail.next
    tail.next = moving.next
    moving.next = before.next
    before.next = moving
```

`before` never moves. Each round takes the node sitting after `tail` and puts
it at the front of the range. After `right - left` rounds the range is
reversed and both of its ends are already attached.

**The dummy node is the point.** Without it, `left == 1` has no predecessor
and needs a branch; with it, every position has one and the head is just
`dummy.next` at the end. It is the standard cure for "the first node is
special" in any list problem.

## What the twist was testing

Whether reversing was understood as pointer surgery or as a recipe for one
case. Copying the values into a list and writing them back reversed passes a
check on values and fails this one, which looks at which node is where.

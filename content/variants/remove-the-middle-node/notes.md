# Twice the speed, half the distance

Revealed after grading. This is "Delete the Middle Node of a Linked List"
(LeetCode 2095).

Removing the nth node from the end used two pointers held `n` apart. The
middle cannot be reached that way, because how far it is from either end
depends on a length you do not have. What it is, instead, is *half way* — and
a pointer moving at double speed measures halves.

```python
slow = head
fast = head.next.next
while fast is not None and fast.next is not None:
    slow = slow.next
    fast = fast.next.next
slow.next = slow.next.next
```

**The head start is the detail.** Starting both pointers at the head leaves
`slow` *on* the middle, which is one node too far to unlink it. Starting
`fast` two ahead leaves `slow` on the predecessor.

Fixed gap for "nth from the end"; fixed ratio for "the middle", "a third of
the way" and cycle detection. Both are ways of measuring a list you may only
walk once.

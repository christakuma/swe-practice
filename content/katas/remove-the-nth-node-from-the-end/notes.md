# Remove the Nth Node From the End — let the gap do the counting

Revealed after grading. The problem is the classic one (LeetCode 19); the
wording above is ours. The one-pass constraint is the whole exercise — without
it this is a two-line problem, and with it you have to find a way to know
something about the end of the list before you get there.

## Why two passes is the obvious answer

Walk the list, count the nodes, then walk again to position `length - n`.
Correct, `O(n)` time, `O(1)` space — and it reads the list twice. Nothing is
*wrong* with it, and if the list were on disk or arriving over a socket you
could not do it at all, which is the real reason the one-pass version is worth
having.

## The move

You cannot count backwards from the end of a singly linked list. So stop
trying to, and arrange for something else to arrive at the end at a known
distance from the node you want:

```python
dummy = ListNode(0, head)
front = behind = dummy
for _ in range(n):
    front = front.next
while front.next is not None:
    front, behind = front.next, behind.next
behind.next = behind.next.next
return dummy.next
```

Two pointers, a fixed gap of `n`, moved in step. When `front` reaches the last
node, `behind` is sitting one short of the doomed node — which is exactly where
it has to be, because **unlinking a node requires the node before it.** There
is no route backwards, so aiming directly at the target is useless.

The gap is doing the counting. That is the idea worth keeping: *a fixed offset
between two cursors converts "n from the end" into "the end", and the end is
something you can detect.*

## The dummy node, again

Removing the head is not a smaller case of removing a middle node — it is a
different shape, because the head has no predecessor to write through. Without
a sentinel you need:

```python
if n == length:
    return head.next
```

...which requires the length, which is the thing the one-pass version refuses
to compute. The dummy lends the head a predecessor, and then `dummy.next` is
the right answer in every case — including the one-node list, where it comes
out None for free.

`test_removes_the_head` is the discriminating test in this file for exactly
this reason: a solution without the sentinel passes every other test and either
crashes or silently drops nothing on that one.

## Starting both pointers at the dummy

This is the off-by-one everybody hits. Start them at `head` and advance `front`
n times, and `behind` lands *on* the target rather than before it — so you
unlink the wrong node, consistently one too late. Starting both at the dummy
builds the one-short offset into the setup instead of correcting for it later
with an `n + 1` that nobody can read.

If you prefer, the same thing stated as an invariant: **`behind` is always `n`
nodes behind `front`, and `front` stops on the last node, so `behind` stops on
the (n+1)th-from-last — the predecessor.**

## What to take away

The two-cursor-with-a-gap pattern is the generalisation, and it is everywhere
once you see it: the fast/slow pair that finds a cycle, the pair that finds the
middle of a list, the sliding window over an array. All of them are the same
trick — *maintain a relationship between two cursors so that one of them
reaching a boundary tells you something about the other.*

The sentinel is the other half, and it is not specific to this problem: when a
linked-list operation has an awkward first element, a dummy node usually
deletes the branch rather than hiding it.

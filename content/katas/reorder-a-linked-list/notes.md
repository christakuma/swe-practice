# Reorder a Linked List — three known moves, composed

Revealed after grading. The problem is the classic one (LeetCode 143); the
wording above is ours. Nothing in it is new if you have done
[reverse a linked list](../reverse-a-linked-list/notes.md) and met the
fast/slow pointer pair — and that is exactly why it is worth doing. Most real
work is composition, and composition has its own failure modes that the parts
do not.

## The shape of the answer

You need the list from the back, and a singly linked list only goes forwards.
So make the back go forwards:

1. **Find the middle** — slow pointer, fast pointer at double speed.
2. **Sever and reverse the second half** — now it reads back-to-front.
3. **Weave** — one node from each half, in turn.

```python
slow = fast = head
while fast.next is not None and fast.next.next is not None:
    slow, fast = slow.next, fast.next.next

back = slow.next
slow.next = None          # sever before reversing

behind = None              # the reversal from the earlier kata
while back is not None:
    back.next, behind, back = behind, back, back.next

front = head               # the weave
while behind is not None:
    front_ahead, behind_ahead = front.next, behind.next
    front.next, behind.next = behind, front_ahead
    front, behind = front_ahead, behind_ahead
```

`O(n)` time, `O(1)` space.

## The bug that composition introduces

`slow.next = None` is the line people leave out, and leaving it out is not a
small error. Without the cut, the first half's tail still points into the
second half. After the reverse, that pointer aims at the second half's *new
tail* — so the weave links the list into a **cycle**. The first few values come
out correct and then the walk never stops.

This is why `test_terminates_rather_than_closing_a_cycle` reads with a step
limit rather than trusting termination. A test that just walked the list would
hang instead of failing, which in a grading harness means a timeout and a
useless message.

**The general lesson: when you split a structure in order to transform half of
it, severing is part of the split.** A "half" that still points at the other
half is not a half.

## Which half gets the middle node

The loop condition decides it. `fast.next and fast.next.next` stops `slow` on
the **last node of the first half** for both parities — so on an odd length the
first half takes the extra node and the second half is never longer.

That is not cosmetic. It is what lets the weave be driven by `behind` running
out: the front half always has at least as many nodes, so when the reversed
back half is exhausted the weave is finished and the last `front_ahead` write
has already terminated the chain. Use `fast and fast.next` instead and `slow`
lands one further on, the second half comes out longer on odd lengths, and the
weave drops its final node.

Pick a convention and let the loop enforce it, rather than correcting for the
parity afterwards with an `if len % 2`.

## Relink, don't copy values

```python
nodes = collect(head)
values = interleave(nodes)
for node, value in zip(nodes, values):
    node.value = value      # wrong answer, right walk
```

The walk comes out correct and every node now holds someone else's value. If
anything else in the program is holding a reference to the third node expecting
it to be the third node, you have broken it. `test_reuses_the_nodes_it_was_given`
checks the original node objects still carry their original values, which is
the only way to see the difference.

The same reason `reorder_list` returns `None`: the caller keeps the head it
passed in, so the reorder has to be visible *through that reference*. Building
the right order onto a fresh head is a function that appears to do nothing.

## What to take away

The fast/slow pair is the reusable half. Finding the middle in one pass is the
same idea as the fixed-gap pair in
[remove the nth node](../remove-the-nth-node-from-the-end/notes.md): maintain a
relationship between two cursors so that one hitting a boundary tells you
where the other is. Double speed gives you the midpoint; a fixed gap gives you
an offset from the end; equal speed from different starts gives you the
intersection of two lists.

And when a problem reduces to operations you already have, the risk moves out
of the operations and into the seams between them. Here the entire difficulty
is one line that belongs to neither the split nor the reverse.

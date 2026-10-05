# Merge K Sorted Lists — the heap replaces a scan

Revealed after grading. The problem is the classic one (LeetCode 23); the
wording above is ours. It is the natural sequel to
[merge two sorted lists](../merge-two-sorted-lists/notes.md), and the
interesting part is that the *merge* does not change at all — only the way you
find the next smallest node.

## What the two-list merge was really doing

At every step it asked: **which of the current front nodes is smallest?** With
two lists that is one comparison, so the question is invisible. With k lists
the same question costs a linear scan, and you ask it once per output node:

```python
O(k) per node x kn nodes = O(k * kn)
```

For k = 1000 and n = 100 that is about fifty million node visits. The question
is the bottleneck, not the merging.

## The move

"Give me the smallest of these k things, repeatedly, while I keep putting more
in" is the job description of a **min-heap**. Substituting one for the scan
takes the per-node cost from `O(k)` to `O(log k)`:

```python
heap = [(head.value, i, head) for i, head in enumerate(lists) if head is not None]
heapq.heapify(heap)

dummy = ListNode(0)
tail = dummy
while heap:
    _, index, node = heapq.heappop(heap)
    tail.next = node
    tail = node
    if node.next is not None:
        heapq.heappush(heap, (node.next.value, index, node.next))
return dummy.next
```

`O(kn log k)` time, `O(k)` space.

## One entry per list, not one per node

This is the detail that separates a correct solution from the intended one.
Pushing every node up front also works — you get a heapsort over all `kn`
nodes, `O(kn log kn)` time and `O(kn)` space — and it throws away the fact
that each list is **already sorted**. Holding only the k fronts is what
exploits that: the smallest unused node is always one of them, because
everything behind a front is larger than it.

Same idea as the two-list merge, which never needed to look past the two
heads. The heap is a bookkeeping upgrade, not a different algorithm.

## The tiebreaker is load-bearing

`heapq` compares the tuples you give it. On a tie in the first element it moves
to the second — and if the second is a `ListNode`, Python raises:

```
TypeError: '<' not supported between instances of 'ListNode' and 'ListNode'
```

So `(value, node)` works perfectly until two lists hold the same value, which
is the first realistic input. `test_handles_equal_values_across_lists` is built
entirely out of ties for that reason.

Using the **originating list's index** as the tiebreaker does two things at
once. Because the heap holds at most one entry per list, those indices are
distinct at every moment — so the tie always resolves and never reaches the
node. And it resolves toward the earlier list, which makes the merge *stable*,
the same property `<=` bought in the two-list version. A monotonically
increasing counter also prevents the crash, but it loses the stability after
the first round, for nothing.

## Why no final sever

The last node emitted is necessarily one whose `next` was already `None` — had
it had a successor, that successor would have been pushed and the loop would
have run again to emit it. So the result terminates on its own.

Worth working out rather than adding `tail.next = None` defensively: during the
loop each emitted node *does* still point into its source list, and relying on
"the next append overwrites it" is a real invariant that is worth being able to
state. `test_terminates_rather_than_running_into_a_source_list` is what holds
it.

## The other good answer

Divide and conquer gets the same bound without a heap: pair the lists up and
merge pairwise, halving the count each round. `log k` rounds, `O(kn)` work per
round, `O(kn log k)` total — and it reuses your two-list merge verbatim, which
is a strong argument for it in an interview.

The heap wins when the lists arrive over time rather than all at once, because
it never needs to know k in advance. That is the version this one is written
for, and it is also the shape of an external merge sort: k sorted runs on disk,
one buffer each, a heap over the fronts.

## What to take away

**When a loop's inner step is "find the smallest/largest so far", a heap
usually deletes it** — the same way a dict deletes a membership scan in
[two sum](../two-sum/notes.md). Top-k, the median of a stream, Dijkstra's
frontier and task scheduling are all this one move with different bookkeeping
around it.

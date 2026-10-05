# Merge Two Sorted Lists — what the dummy node buys

Revealed after grading. The problem is the classic one (LeetCode 21); the
wording above is ours. It is worth doing carefully because it is the merge step
of merge sort, and because it is the cleanest possible argument for a technique
you will reach for constantly afterwards.

## The move

Both inputs are sorted. That single fact means the smallest node you have not
used yet is **always at the front of one list or the other** — so there is
never anything to search for, only two candidates to compare.

```python
dummy = ListNode(0)
tail = dummy
while first is not None and second is not None:
    if first.value <= second.value:
        tail.next, first = first, first.next
    else:
        tail.next, second = second, second.next
    tail = tail.next
tail.next = first if first is not None else second
return dummy.next
```

`O(n + m)` time, `O(1)` space.

## The dummy node

Write this without one and watch what happens. The first append has no tail to
append to, because the result is still empty — so you need a branch:

```python
if head is None:
    head = tail = chosen
else:
    tail.next = chosen
    tail = chosen
```

That `if` is false on every iteration but the first, and it is *inside the
loop*, so you pay for it n times and read it every time you come back to the
code. Hoisting it above the loop is worse: now you have the comparison logic
twice.

One throwaway node deletes the special case outright. `tail` always exists, so
the loop body has exactly one shape, and `dummy.next` is the real head at the
end — which is also the answer to "what if the result starts in the *second*
list?", a case that trips solutions trying to return `first`.

**The general form: when a linked-list algorithm has an awkward first or last
element, a sentinel node usually removes the branch rather than hiding it.**
Remove-the-nth-node and reorder-a-list both want one.

## The tail splice

When one list runs out, the other is already sorted and already linked. Attach
it whole:

```python
tail.next = first if first is not None else second
```

One write. Walking the remainder node by node is the same answer and turns a
clean `O(1)`-space merge into pointless work; forgetting it altogether silently
truncates the result, which is why `test_attaches_the_whole_remainder` uses
lists of wildly different lengths — equal-length inputs cannot see that bug.

## Stability, and `<=` vs `<`

`first.value <= second.value` takes from the first list on a tie. The prompt
says equal values may come out in either order, so both pass — but the `<=`
version is **stable**, meaning equal elements keep their original relative
order. That costs nothing here and is exactly the property a merge sort built
on this function needs in order to be a stable sort. Worth taking for free.

## Splice, don't rebuild

```python
values = sorted(walk(first) + walk(second))
return build(values)
```

Right values, wrong answer — the caller's node objects are still linked the old
way, and you have spent `O(n + m)` extra space plus a sort to avoid a
comparison you already had. `test_reuses_the_nodes_it_was_given` asserts
identity, because value equality genuinely cannot tell the two apart.

## What to take away

This function is the merge in merge sort, which is why merging *k* lists is a
separate kata rather than a harder version of this one: once you have this,
the k-list problem is a question about *which two to merge next*, and that is a
heap. The pieces compose.

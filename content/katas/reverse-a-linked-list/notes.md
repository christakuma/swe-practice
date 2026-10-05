# Reverse a Linked List — three names, one pass

Revealed after grading. The problem is the classic one (LeetCode 206); the
wording above is ours. It is on every list because it is the smallest problem
that is *only* about pointer discipline — there is no algorithm to discover and
nowhere for cleverness to hide.

## The move

Nothing moves. Every node stays exactly where it was allocated. The only thing
that changes is which node each `next` points at, and you can turn every arrow
around in a single walk if you carry the node behind you:

```python
behind = None
node = head
while node is not None:
    ahead = node.next
    node.next = behind
    behind = node
    node = ahead
return behind
```

`O(n)` time, `O(1)` space. Three names: the node behind you, the node you are
on, the node ahead.

## Why the line order is the entire exercise

`node.next` is the only route to the rest of the list. Once you overwrite it,
everything past this node is unreachable — so `ahead = node.next` has to happen
*before* `node.next = behind`. Swap those two lines and the list is severed at
the first node, `node = ahead` walks into the node you just came from, and you
either loop forever or return a two-node list.

This is worth more than a memorised sequence: **when a pointer is both the thing
you are overwriting and the thing you need next, read it first.** The same
obligation shows up in every in-place relink — removing a node, reordering a
list, reversing in groups of k.

## The two details the tests are actually checking

**Seed `behind` as None, not as `head`.** The original head becomes the new
tail, and a tail's `next` must be None. Leave it pointing at its old successor
and you have not built a reversed list, you have built a **cycle** — the values
come out right for a few steps and then never stop. `test_does_not_leave_a_cycle`
reads with a step limit rather than trusting the walk to terminate, which is the
only way a test suite can fail this safely instead of hanging.

**Relink, don't rebuild.** This returns the right values:

```python
values = walk(head)
return build(reversed(values))   # a fresh chain of new nodes
```

It passes every value-equality test and it is the wrong answer to the question
asked, because the caller's existing node objects are still linked the old way.
`test_reuses_the_nodes_it_was_given` asserts `result is nodes[-1]` — object
identity, not equality. That is the discriminating test in this file, and it is
there because value comparison genuinely cannot see the difference.

## Recursion, and why the long-list test exists

The recursive version is elegant and costs a stack frame per node:

```python
def reverse_list(head):
    if head is None or head.next is None:
        return head
    new_head = reverse_list(head.next)
    head.next.next = head
    head.next = None
    return new_head
```

`O(n)` space, and on CPython it raises `RecursionError` a thousand nodes in.
The declared bound on this kata is `O(1)` space, so
`test_reverses_a_list_too_long_to_recurse_over` is where that claim is tested
rather than merely written down. Worth knowing both: the recursive one is the
better *explanation* of why the reversal works, and the iterative one is the
one you ship.

## What to take away

Reversal is the base case for a family of problems that are all this loop with
a bound on it — reverse the first k nodes, reverse between positions i and j,
reorder a list by interleaving its halves (reverse the back half, then zip).
Getting the three-name loop into your hands once means those are variations
rather than new problems.

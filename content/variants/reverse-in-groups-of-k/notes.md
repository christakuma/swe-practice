# Reversal is the easy third

Revealed after grading. This is "Reverse Nodes in k-Group" (LeetCode 25).

Reversing a list is three pointers and one loop, and that loop is in here
unchanged. Everything hard about this problem is around it.

## 1. Look before you reverse

A short final group must be left alone. If you reverse first and count
afterwards, you find out too late and have to reverse it back. So walk `k`
nodes ahead first:

```python
last = before
for _ in range(k):
    last = last.next_node
    if last is None:
        return dummy.next_node
```

## 2. Reverse exactly `k`

The standard loop runs until it falls off the end. This one runs `k` times.
The trick worth knowing is the starting value of `previous`: not `None`, but
**the node after the group**. The first node of the group is relinked to
`previous` on the first iteration — so it ends up pointing past the group,
which is exactly where the group's new tail should point.

## 3. Stitch

Before: `before -> first ... last -> after`.
After: `before -> last ... first -> after`.

Step 2 already made `first` point at `after`. What is left is
`before.next_node = last` (which is `previous` when the loop ends), and then
`before = first`, because `first` is now the node in front of the next
group.

The stitch people forget is that one — the link *into* the reversed group
from the group before it. Without it the first group's tail still points at
the second group's old head, and half of every later group is unreachable.

## The dummy node

The first group has no node before it, and the head of the whole list
changes. A dummy in front makes the first group like every other and gives
you something to return.

## What the twist was testing

Decomposition under pressure. The recursive version — reverse the first `k`,
recurse on the rest — is shorter and uses a stack frame per group, which
fails for thirty thousand nodes in pairs. The iterative version is three
small, separately checkable steps, and the skill is keeping them separate.

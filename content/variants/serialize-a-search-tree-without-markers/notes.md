# The search property is the missing markers

Revealed after grading. This is "Serialize and Deserialize BST"
(LeetCode 449).

An arbitrary tree with `n` nodes needs its shape written down: pre-order
with a marker for every absent child costs `2n + 1` tokens. Take the markers
out and `1,2` could be a root with a left child or a root with a right
child, with no way to tell.

A search tree can tell. In `5,3` the 3 is smaller, so it is on the left. In
`5,8` the 8 is larger, so it is on the right. The comparison *is* the
marker.

## Which order?

- **In-order** is the values sorted. It is identical for every search tree
  holding those values — five different trees on `1, 2, 3`, one string. It
  carries no shape at all.
- **Pre-order** lists a node before its descendants. After the root, the
  smaller values are its left subtree and the larger ones its right, and
  the same rule applies inside each. Shape fully determined.
- **Level-order** and **post-order** also work, read forwards and backwards
  respectively. Pre-order is the easy one.

## Rebuilding

It is the kata "rebuild a search tree from pre-order": a stack of nodes whose
right child is still open, or a recursion that carries an upper bound. Both
are linear.

Inserting the values into an empty search tree, in pre-order, also gives the
right tree — each node arrives after all its ancestors and so lands where it
was. That is `O(n * h)`: fine for a balanced tree, quadratic for a chain.

## What the twist was testing

A sense of how much information a format has to carry. The standard problem
teaches that structure must be recorded. This one shows when it need not be:
when an invariant of the data already determines it. Sorted arrays need no
indices, a complete binary tree needs no pointers, and a search tree needs no
null markers — each time, the constraint is doing a serialiser's job.

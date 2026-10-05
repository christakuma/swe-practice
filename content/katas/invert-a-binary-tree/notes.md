# Invert a Binary Tree — the structure is the algorithm

Revealed after grading. The problem is the classic one (LeetCode 226); the
wording above is ours. It is famous for a tweet about a rejected interview
candidate, and it is in the library for a less dramatic reason: it is the
shortest problem where the recursive decomposition is *all* there is, with no
accumulator and no ordering decision to obscure it.

## The move

```python
if root is None:
    return None
root.left, root.right = invert(root.right), invert(root.left)
return root
```

Swap the root's children; solve the same problem on each. `O(n)` time, `O(h)`
space for the stack.

The `None` check does two jobs: it answers the empty tree and it terminates the
recursion at the leaves. A separate leaf check — `if root.left is None and
root.right is None` — is work that the base case already does.

## Why pre- or post-order both work here

Worth understanding rather than just noticing, because it is **unusual**.

```python
root.left, root.right = root.right, root.left   # swap first
invert(root.left)
invert(root.right)
```

Also correct. The two recursive calls operate on **disjoint subtrees**, so
neither can observe the other's work, and the swap only rewrites pointers *at
this node* — nothing in the recursion reads a pointer the swap changes.

Most tree algorithms have no such freedom. Anything that accumulates a result
(`max-depth`, `binary-tree-maximum-path-sum`) must recurse before combining,
because the combination needs the children's answers. Anything whose recursion
depends on position (`validate-a-binary-search-tree`) must push information
down before descending. The order being free here is a consequence of the
operation being purely local, and recognising *why* tells you when you do not
have that freedom.

## In place means the caller's root

```python
def invert(root):
    if root is None:
        return None
    return TreeNode(root.value, invert(root.right), invert(root.left))
```

This returns a correctly mirrored tree and leaves the caller's tree untouched.
If the caller keeps its own reference — which it does — the function appears to
have done nothing. `test_returns_the_node_the_caller_holds` checks the returned
root **is** the original object, and `test_reuses_the_nodes_it_was_given`
checks the children were relinked rather than having their values copied
around.

Same distinction as in [reverse a linked list](../reverse-a-linked-list/notes.md):
relinking and rebuilding produce equal structures and are not the same answer.

## The property test

`test_inverting_twice_returns_the_original` leans on mirroring being an
**involution**. It holds for any tree, needs no expected-value table, and
catches an "inversion" that is self-consistent but is not a mirror.

That is the third time this pattern has earned its place in the library —
alongside four rotations in
[rotate a matrix](../rotate-a-matrix-in-place/notes.md) and double reversal in
[reverse the bits of a word](../reverse-the-bits-of-a-word/notes.md). **When an
operation is its own inverse, say so in a test**; it is cheaper to write than
examples and covers inputs you would not think to enumerate.

## The recursion limit is real

`O(h)` stack space is `O(log n)` for a balanced tree and `O(n)` for a
degenerate one. A tree that is effectively a linked list — which is what you
get from inserting sorted data into an unbalanced BST — will raise
`RecursionError` around a thousand nodes on CPython.

The iterative version is a queue or stack and is barely longer:

```python
stack = [root]
while stack:
    node = stack.pop()
    if node is None:
        continue
    node.left, node.right = node.right, node.left
    stack.extend((node.left, node.right))
```

Worth having when the depth is not known to be bounded. Worth not reaching for
first, because the recursive version is the problem statement written down.

## What to take away

**When a problem's recursive structure matches its data's recursive structure,
the solution is usually that structure with one line in it.** The useful skill
is spotting which line — here a swap, in `max-depth` a `max`, in `same-tree` an
`and`. Reaching for a traversal and a loop when the shape already recurses is
how simple tree problems become long ones.

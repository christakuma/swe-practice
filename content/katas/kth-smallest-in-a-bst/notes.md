# Kth Smallest in a BST — the traversal is the ordering

Revealed after grading. The problem is the classic one (LeetCode 230); the
wording above is ours. The pleasing thing about it is that a correct solution
contains no comparison, no sort and no mention of "smallest" — the ordering is
carried entirely by the shape of the walk.

## The move

**An in-order traversal of a BST visits its values in increasing order.** So
the kth node visited *is* the kth smallest, and the problem reduces to
"traverse in order, stop at k".

```python
stack, node, remaining = [], root, k
while stack or node is not None:
    while node is not None:          # push the whole left spine
        stack.append(node)
        node = node.left
    node = stack.pop()               # visit
    remaining -= 1
    if remaining == 0:
        return node.value
    node = node.right
```

`O(h + k)` time, `O(h)` space.

Worth noticing what is *absent*. Nothing in that code says `<`. The BST
property is never checked or used explicitly — it is the reason in-order
produces sorted output, and that reason lives in the traversal, not in the
code. Run the same function on an arbitrary binary tree and it returns the kth
node in in-order, which is a meaningless answer delivered confidently.

## Why an explicit stack

Recursion can do this. Stopping early is the problem: the answer has to climb
back through every frame, which means a sentinel return value, an exception, or
a mutable counter in an enclosing scope.

```python
def walk(node):
    if node is None or found:
        return
    walk(node.left)
    ...                    # nonlocal counter, nonlocal answer, early-exit flag
```

All three work and all three are noisier than the thing they are implementing.
With a stack, "stop now" is a plain `return` and the untouched nodes are simply
never pushed.

**That is the general reason to reach for an explicit stack: not performance,
but control over when to stop.** Recursion is the better default when you
consume the whole structure; it fights you when the point is to leave early.

## Stopping is part of the specification

```python
values = []
inorder(root, values)
return values[k - 1]
```

Correct, `O(n)` time, `O(n)` space — and on a million-node tree with `k = 1` it
reads a million nodes to answer a question about one. The intended solution
walks the left spine and pops once.

The suite checks this with a **landmine**: a `TreeNode` subclass whose every
attribute access raises, planted as the root's right child.

```python
tree = bst([1, 2, 3])
tree.right = Landmine()
assert kth_smallest(tree, 1) == 1
```

Everything in that subtree is larger than the root, so a correct solution has
no reason to touch it. Verified against the collect-everything version, which
trips it.

Same technique as the `Tripwire` list in
[contains a duplicate](../contains-a-duplicate/notes.md), and the same reason:
**a test that can only see return values cannot see effort.** When the
requirement is about what the code *does not* read, you need an input that
objects to being read.

## The traversal order is the whole answer

`test_walks_in_order_not_level_order` builds a tree whose root is the median.
A pre-order or breadth-first walk returns the root first, so `k = 1` gives `5`
instead of `2`. The test asserts `kth_smallest(tree, 1) != tree.value`
explicitly, because "returns something plausible from the right tree" is the
failure mode and a single expected value does not expose it.

## If you need this often

Augment the tree: store, at each node, the size of its subtree. Then finding
the kth smallest is a descent — compare `k` with the left subtree's size and go
left, stop, or go right with `k` reduced — which is `O(h)` rather than
`O(h + k)`, and `O(log n)` on a balanced tree regardless of `k`.

That is the right answer when the query is frequent, and it costs you
maintaining the counts through every insert and delete. The classic trade:
precomputation that has to be kept honest. Worth knowing the option exists; not
worth building for one query.

## What to take away

**Pick the traversal that makes the property you need fall out, rather than
computing the property.** In-order on a BST gives you sorted order for free;
level-order gives you distance from the root; post-order gives you children
before parents. A surprising number of tree problems are "which order?" plus
one line.

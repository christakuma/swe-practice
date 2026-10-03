# One return value carrying three different meanings

```python
if node.value in (first, second):
    return node.value          # "I am one of them"
left  = search(node.left,  first, second)
right = search(node.right, first, second)
if left is not None and right is not None:
    return node.value          # "they split here, so I am the ancestor"
return left if left is not None else right   # "pass the report up"
```

The function returns the same *type* for three different claims, and the parent
can tell them apart from how many of its children reported something. That
overloading is unusual enough to be worth noticing, because it is what makes the
solution three lines instead of a search for two paths and a comparison.

Why it is correct: if both children report non-`None`, the two values are in
different subtrees, so no node below this one has both — and this one does. If
only one child reports, both values are in that subtree (or only one exists
there), and the answer is whatever that subtree said.

## Why "a node is its own ancestor" falls out for free

`lca(5, 4)` is `5`, and nothing in the code special-cases it. When the recursion
reaches `5`, it returns immediately — before looking at its children, where `4`
lives. The parent sees one report and passes it up. The convention and the early
return are the same line.

If the convention were the other way — a node is *not* its own ancestor — the
code would get materially longer: you would have to keep searching below a
matched node to find out whether the other value is there, and return the parent
instead. Worth noticing that a one-sentence specification choice is doing that
much work.

## The explicit-path alternative

Find the root-to-node path for each value, then walk both paths together and
take the last common element.

```
7: [3, 5, 2, 7]
4: [3, 5, 2, 4]
            ^ last common -> 2
```

Also O(n) time, O(n) space for the two paths, and genuinely easier to explain
and to debug. It is the version to write if the recursive one is not obvious yet,
and the one to reach for when you need the paths anyway — "how far apart are
these two nodes" is a path question, and the answer is
`len(path_a) + len(path_b) - 2 * depth(lca)`.

## On a search tree it is a different problem

With the search tree property, no backtracking is needed at all:

```python
while node:
    if first < node.value and second < node.value:
        node = node.left
    elif first > node.value and second > node.value:
        node = node.right
    else:
        return node.value          # the values split here
```

O(h) instead of O(n), iterative, no recursion. "The values are on opposite
sides, or one of them is this node" is exactly the splitting condition the
general version has to *discover* by searching — and here the ordering tells you
for free. A good reminder that the right algorithm depends on what the data
structure promises, not on what shape it has.

## Why the presence check is separate

Without it, `lca(5, 99)` returns `5`: the recursion found one value, nothing
contradicted it, and the report travelled to the root. The answer is confidently
wrong, which is worse than an error.

Two full traversals is the honest cost of not having that guarantee — or one
traversal returning both an ancestor and a count of how many of the two values
were seen, which is the version to write if the tree is large and you mind
walking it twice.

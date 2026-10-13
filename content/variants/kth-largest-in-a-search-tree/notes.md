# In-order backwards

Revealed after grading. The mirror of "Kth Smallest Element in a BST"
(LeetCode 230).

An in-order walk — left, node, right — reads a search tree in ascending
order. Swap the two sides and it reads in descending order:

```python
while node is not None:
    stack.append(node)
    node = node.right       # was .left
node = stack.pop()
...
node = node.left            # was .right
```

That is the entire change. The reason it is worth doing as an exercise is the
alternative that suggests itself: find the size `n`, then ask for the
`(n - k + 1)`th smallest. That is correct and has to visit the whole tree to
learn `n`, which throws away the one property that made the original
interesting — stopping after `k` nodes.

When a problem is the mirror image of one you know, mirror the *algorithm*.
Translating the question back into the old one usually costs something the
direct version would not.

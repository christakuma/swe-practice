# One bound inclusive, one exclusive

Revealed after grading. A convention change to "Validate Binary Search Tree"
(LeetCode 98) — the kind of follow-up that starts "and what if duplicates are
allowed?"

The strict version passes a range down the tree and requires
`low < value < high`. Allowing repeats on the left changes one comparison:

```python
if not above < node.value <= at_most:
    return False
return within(node.left, above, node.value) and within(node.right, node.value, at_most)
```

Going left, the node's own value becomes the *inclusive* upper bound. Going
right, it becomes the *exclusive* lower bound.

**It has to be the bounds.** The tempting patch is local: "a left child may
equal its parent". But a repeat can be many levels down — the right child of a
left child, say — and still be in the left subtree of the value it repeats.
Only a bound inherited from the ancestor can see that. The same goes for the
bad case: a left child that equals a value two levels up *on the right-hand
path* looks fine locally and is not.

Before coding any tree with duplicates, pin the convention down — which side
do equal values go? — and write one example of each as a test.

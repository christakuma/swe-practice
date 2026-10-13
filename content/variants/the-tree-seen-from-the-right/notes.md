# "Rightmost" is a fact about a level

Revealed after grading. This is "Binary Tree Right Side View" (LeetCode 199).

The picture in the prompt invites the wrong program:

```python
while node is not None:
    seen.append(node.value)
    node = node.right
```

Walk the right spine. It is right for the top of every tree, and it stops the
moment the spine does — while the left subtree may carry on for many more
levels, every one of which is visible from the right because nothing stands
in front of it.

```
      1
     / \
    2   3        seen from the right: 1, 3, 4
   /
  4
```

"Rightmost on its level" is a property of a whole level, so the solution is
the level-order traversal, keeping one value per level instead of all of
them:

```python
while level:
    seen.append(level[-1].value)
    level = [child for node in level for child in (node.left, node.right) if child]
```

## The depth-first version

There is a neat alternative: walk depth-first visiting the **right child
first**, and record a node's value only if its depth has not been seen
before. The first node met at each depth is then the rightmost. It works, and
the right-before-left order is the whole of it — swap the two and you have
the view from the left.

## What the twist was testing

Whether level-order traversal was understood as a way of answering questions
about levels, or just as a way of producing a list of lists. Largest value
per level, average per level, the leftmost node of the bottom level, whether
the tree is complete — all the same loop, with a different thing kept from
each round.

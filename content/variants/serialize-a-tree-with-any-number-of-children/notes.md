# Write down how many children

Revealed after grading. This is "Serialize and Deserialize N-ary Tree"
(LeetCode 428).

A binary tree was serialised by marking each absent child, which works
because every node has exactly two slots. A node with a *list* of children has
no fixed slots, so there is nothing to mark. What pins the shape down instead
is each node's child count:

```
1 3  3 2  5 0  6 0  2 0  4 0
```

value, count, in pre-order. Without the counts, `1 2 3` could be a chain or a
fan; with them the two are `1 1 2 1 3 0` and `1 2 2 0 3 0`.

Reading it back needs a stack of nodes still owed children:

```python
while owed[-1][1] == 0:
    owed.pop()
parent = owed[-1][0]
owed[-1][1] -= 1
```

**Loops, not recursion.** Both directions are naturally recursive, and both
fail on a tree ten thousand levels deep. An explicit stack is the same
algorithm without the limit.

"Missing-child markers" and "child counts" are two encodings of the same
information. Knowing why each works for its tree — a fixed number of slots
versus a variable one — is what lets you pick the right one for a third.

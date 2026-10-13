# A dict from old to new

Revealed after grading. This is "Copy List with Random Pointer"
(LeetCode 138).

It is the graph-cloning problem in a different shape. The trouble in both is
that a pointer may lead somewhere not yet copied, and the cure in both is a
dict from each original node to its copy.

```python
copies[node] = Node(node.value)          # pass 1: every node gets a copy
...
copy.next = copies[node.next]            # pass 2: pointers, by lookup
copy.random = copies[node.random]
```

Two passes mean every target already exists when a pointer is set, whichever
way it points. Mapping `None` to `None` removes the special cases.

**The shallow copy is the bug.** Setting `copy.random = node.random` produces
a list that looks right when printed and points into the original. It shows
only when someone modifies one list and the other changes — which is why the
tests compare identities and not only values.

There is an `O(1)`-space version that weaves the copies into the original
list and unpicks them afterwards. Know that it exists; write the dict.

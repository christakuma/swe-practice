# Turn the tree upside down and it is two linked lists

Revealed after grading. This is "Lowest Common Ancestor of a Binary Tree III"
(LeetCode 1650).

The standard problem is a search: start at the root, look down both sides,
report where the two targets were found. Without the root there is nothing to
search *from*. But with parent pointers you do not need to search at all.

From any node, `parent` leads to the root along exactly one path. So each
given node is the head of a singly linked list, and the two lists share a
tail — the common ancestors, ending at the root.

```
first:   7 -> 2 -> 5 -> 3
second:            6 -> 5 -> 3
                        ^ where they join
```

"Lowest common ancestor" is "the node where two linked lists intersect", and
`left` and `right` are never read.

## Lining up the two chains

If both nodes were equally deep, walking both up in step would meet at the
join. When they are not, there are two ways to line them up:

**Measure and trim.** Count each node's depth, climb the deeper one by the
difference, then climb in step.

**Swap heads.** Climb in step; when a pointer runs off the top, restart it
at the *other* node:

```python
while a is not b:
    a = a.parent if a is not None else second
    b = b.parent if b is not None else first
```

Each pointer walks one chain and then the other, so after `len(A) + len(B)`
steps both have covered the same distance and sit the same height below the
join. Five lines, no arithmetic.

Climbing both in step *without* either correction walks the shallower pointer
off the top while the deeper one is still below the answer.

## What the twist was testing

Recognising a problem you have already solved when it arrives in different
clothes. "Tree" suggests recursion and a search from the root; the structure
you are actually given is a pair of linked lists. Asking "what does this
data let me follow?" before "what is this problem called?" is the habit.

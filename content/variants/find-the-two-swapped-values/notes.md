# Flatten it in your head

Revealed after grading. This is the detection half of "Recover Binary Search
Tree" (LeetCode 99).

Validating a search tree can be done two ways: pass bounds down the tree, or
read the tree in order and check that the values ascend. For validation they
are equivalent. For this problem only the second helps, because it turns a
tree question into a question about a list:

> A sorted list had two of its entries exchanged. Which two?

```
sorted:        10 20 30 40 50
neighbours:    10 30 20 40 50      one drop:  30 > 20
far apart:     10 40 30 20 50      two drops: 40 > 30, 30 > 20
```

- **One drop**: the two values are the drop itself.
- **Two drops**: the larger value is the *first* value of the *first* drop;
  the smaller is the *second* value of the *last* drop.

One rule does both — take the first value of the first drop and the second
value of the last drop — and when there is only one drop, first and last are
the same.

```python
if previous is not None and node.value < previous:
    if larger is None:
        larger = previous
    smaller = node.value        # overwritten if there is a second drop
```

## What does not work

**Looking at each node and its children.** The exchanged values can be two
leaves in different subtrees, each perfectly well ordered against its own
parent. The damage shows only against an ancestor further up — which is the
lesson of the standard problem, and it applies here with more force.

**Taking the first drop and stopping.** Right for neighbours, wrong
otherwise: in `10 40 30 20 50` it reports 40 and 30.

## What the twist was testing

Choosing the representation in which the problem is easy. A search tree is a
sorted sequence with extra structure, and plenty of questions about it —
this one, the kth smallest, the closest pair of values, merging two trees —
are best answered by ignoring the structure and reading the sequence.

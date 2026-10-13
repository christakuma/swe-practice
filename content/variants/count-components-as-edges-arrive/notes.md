# A question asked repeatedly needs a structure, not a search

Revealed after grading.

The standard problem can be solved either way: a depth-first search from each
unvisited node, or union-find. They cost the same and the search is easier to
write. This version breaks the tie. It asks the same question after every
edge, and a search has nothing to carry forward — each one starts from
nothing.

Union-find is the structure that *is* the carried-forward state. The count
starts at `n`, and an edge either joins two components or it does not:

```python
first_root, second_root = find(first), find(second)
if first_root != second_root:
    parent[second_root] = first_root
    components -= 1
counts.append(components)
```

Repeats, self-edges and loop-closing edges all fall into the "does not" case
without being mentioned.

## The union-find bug

```python
parent[first] = find(second)      # wrong: re-points the node
parent[find(first)] = find(second)  # right: re-points its root
```

The first line takes `first` out of whatever group it was in and moves it,
alone, into the other. Add `(0, 1)` then `(0, 2)`: node 0 now points at 2 and
node 1 points at nothing. They were connected and no longer are, so `(1, 2)`
"joins" two components that were already one. The count is right for two
edges and wrong on the third, which is why the tests look past the second.

## What the twist was testing

Recognising an **online** problem. "After each" in a prompt means the answer
has to be maintained, not computed — and whether a method can be updated
cheaply matters more than how fast it runs once. The same shift turns sorting
into a heap and a prefix sum into a Fenwick tree.

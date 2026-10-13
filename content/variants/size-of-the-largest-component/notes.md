# Carry the size at the root

Revealed after grading. The union-find companion to "Number of Connected
Components" (LeetCode 323).

Counting components needed only the merges that happened. Measuring them
needs each group to know how big it is, and the place to keep that is the
root:

```python
parent[second] = first
size[first] += size[second]
```

**Skip equal roots.** In the counting version, forgetting the check costs a
wrong decrement. Here it adds a group's size to itself, and the answer can
exceed the number of nodes.

Union by size was optional before, as an optimisation. Once sizes are stored
anyway it is free, and it is what keeps `find` nearly constant.

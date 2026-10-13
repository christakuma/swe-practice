# Peel a layer at a time

Revealed after grading. The level-by-level form of a topological sort — what
a parallel build system computes. Related to "Parallel Courses"
(LeetCode 1136).

The standard version took one ready name at a time, by a tie-break. Take
every ready name at once and the set is a round; removing it exposes the
next.

```python
for name in current:
    for dependent in dependents.get(name, ()):
        waiting[dependent] -= 1
        if waiting[dependent] == 0:
            following.append(dependent)
```

A name's round is one more than the *latest* round among the things it needs
— it waits for its slowest dependency. That makes the number of rounds the
length of the longest chain, which is the real answer to "how long does the
build take with unlimited workers?".

The heap the standard version needed is gone. A tie-break between ready names
is a question that only exists when you take them one at a time.

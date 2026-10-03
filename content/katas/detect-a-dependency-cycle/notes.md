# One visited set is not enough, and the diamond is why

```
    a
   / \
  b   c
   \ /
    d
```

Walking depth-first from `a`, you reach `d` twice — once via `b`, once via `c`.
That is a revisit, and there is no cycle anywhere. So "I have seen this node
before" cannot be the test.

What makes a cycle is reaching a node that is **still on the path you are
currently walking**. In the diamond, by the time `c` reaches `d`, the walk
through `b` has finished and `d` is no longer on the path. In a real cycle, it
still is.

Hence two sets:

| set | meaning | used for |
|---|---|---|
| `on_path` | nodes in the current chain of calls | detecting the cycle |
| `finished` | nodes whose whole subtree is explored | not doing it twice |

Drop `finished` and the algorithm is still *correct* and becomes exponential:
every diamond re-explores its shared subtree once per path into it. Drop
`on_path` and every diamond is reported as a cycle. Both sets earn their place,
for different reasons.

This is the classic **three-colour** DFS: white (unseen), grey (`on_path`),
black (`finished`), and a cycle is an edge to a grey node — a "back edge".

## Why the iterative version is awkward

A recursive DFS gets the path bookkeeping for free:

```python
def walk(node):
    if node in finished:
        return False
    if node in on_path:
        return True
    on_path.add(node)
    for neighbour in dependencies.get(node, ()):
        if walk(neighbour):
            return True
    on_path.remove(node)        # <- the "on the way back out" step
    finished.add(node)
    return False
```

That `on_path.remove` happens after the loop — on the way *back out* of the
call. An explicit stack has no "back out" moment, so it has to be invented:
push each node twice, once to expand and once to finish.

```python
stack = [(start, False)]
...
node, expanded = stack.pop()
if expanded:
    on_path.discard(node); finished.add(node); continue
```

Write the recursive one first, always. Then transform it if the depth demands —
and here it does: the suite has a ten-thousand-link chain, and Python's limit is
a thousand frames.

## The other way: count incoming edges

```python
# Kahn's algorithm
```

Repeatedly remove a node with no remaining dependencies. If you run out of such
nodes before removing them all, whatever is left is a cycle. Same O(V + E), no
recursion at all, and it produces a
[topological order](../topological-order/notes.md) as a side effect — so if you
want both "is it acyclic" and "in what order", that is the one to write.

DFS wins when you want the cycle *itself*: `on_path` at the moment of detection
is the cycle, which is what turns "your build has a circular dependency" into a
message someone can act on.

## Where this comes up

Every time something has to happen in an order: build targets, module imports,
database migrations, task schedulers, spreadsheet formulas, package managers.
The error message "circular dependency detected" is this algorithm, and the good
implementations print the cycle because they kept `on_path`.

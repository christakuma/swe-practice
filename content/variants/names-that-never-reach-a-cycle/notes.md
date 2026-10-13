# Safety spreads from the leaves

Revealed after grading. This is "Find Eventual Safe States" (LeetCode 802).

Cycle detection answers one question about the whole graph. This asks it
about every name separately — can *this* one be resolved? — and the neat part
is that it does not take one search per name.

A name is safe when everything it depends on is safe. Names with no
dependencies are safe. So peel from the leaves:

```python
waiting[dependent] -= 1
if waiting[dependent] == 0:
    ready.append(dependent)
```

It is a topological sort run in the dependency direction, and the names that
are never reached are precisely the unsafe ones.

**Not just the cycle.** "Names not on a cycle" is the wrong answer: `app`
above is on no cycle and still cannot be resolved, because it waits on one.
Unsafe means *reaches* a cycle, and that is why the propagation has to run
from the safe end rather than the other.

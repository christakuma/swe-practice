# Kahn's algorithm: take whatever is ready, repeat

```
outstanding = how many of my dependencies are not yet emitted
ready       = everything whose count is zero

while ready:
    emit one
    for each thing that depended on it:
        decrement; if zero, it is ready now
```

Each name is emitted once and each edge is examined once, so it is O(V + E) —
plus a log factor here because the ready set is a heap rather than a list.

## Cycle detection comes free

When the loop ends, compare the number of names emitted with the number of names
there were. If any are missing, every one of them still has a non-zero count,
which means each is waiting for something that is also waiting — and a finite
chain of waiting with no end is a cycle.

No second pass, no colours, no path to track. That is the main practical
advantage over the DFS approach in
[`detect-a-dependency-cycle`](../detect-a-dependency-cycle/notes.md), which has
to maintain an on-path set specifically to answer this.

What Kahn's *cannot* easily tell you is which names form the cycle — only that
one exists. The leftovers include everything downstream of the cycle too, so
reporting them as "the cycle" is wrong. If the error message needs the cycle,
DFS is the algorithm.

## Why the dict has to be reversed

```python
dependencies = {"app": ["lib"]}     # app needs lib
dependents   = {"lib": ["app"]}     # emitting lib may unblock app
```

The input says what each name needs; the algorithm needs to know, on emitting a
name, who was waiting for it. Building the reverse index is two lines and skipping
it means re-scanning every name's dependency list after each emission — O(V · E)
instead of O(V + E).

Worth recognising as a pattern: when the traversal runs against the direction the
data is stored in, build the index once rather than searching repeatedly.

## The tie-break is a specification decision

Most dependency graphs have many valid orders. "Any of them" is the usual
statement of the problem, and it makes the function non-deterministic — two
correct implementations disagree, and no test can assert on the output.

Choosing the alphabetically smallest ready name at each step fixes that, and
costs a heap instead of a list: `O(log V)` per push and pop instead of `O(1)`.
That is a real cost for a real benefit, and it is the kind of thing worth being
explicit about in a signature rather than leaving to whatever the data structure
happens to do.

Where it matters outside a kata: reproducible builds. A build order that varies
run to run makes a failure hard to reproduce, so real build systems pin the
tie-break — usually by declaration order rather than alphabetically.

## Names that are only ever dependencies

```python
{"build": ["tools"]}      # "tools" has no entry of its own
```

`tools` belongs in the output. A solution that iterates the dict's keys misses
it, and the first line of the reference exists only to collect the full set of
names from both the keys and the values. It is the most common bug in this
problem and the suite tests it on its own.

## Where this comes up

Build systems, module loaders, migration runners, task queues with
prerequisites, spreadsheet recalculation, package installation order, course
prerequisites. Any time the answer to "what do I do first" is "whatever is not
waiting on anything".

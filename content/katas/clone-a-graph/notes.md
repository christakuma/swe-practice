# Clone a Graph — one map, two jobs

Revealed after grading. The problem is the classic one (LeetCode 133); the
wording above is ours. It is the cleanest illustration of a distinction that
causes a lot of trouble: **marking a node as "seen on this path" and marking it
as "already done" are different operations with different lifetimes.**

## Why the naive recursion hangs

```python
def copy(original):
    return Node(original.value, [copy(n) for n in original.neighbours])
```

Node 1 copies node 2, which copies node 1, which copies node 2. Forever.

And this is not an edge case to handle later — **every undirected edge is
already a cycle**, because it appears in both nodes' neighbour lists. A
two-node graph is enough to hang. `test_terminates_on_a_two_node_cycle` is the
minimum reproduction.

## The move

```python
copies: dict[int, Node] = {}

def copy(original):
    if id(original) in copies:
        return copies[id(original)]
    duplicate = Node(original.value)
    copies[id(original)] = duplicate          # register BEFORE recursing
    duplicate.neighbours = [copy(n) for n in original.neighbours]
    return duplicate
```

`O(V + E)` time, `O(V)` space.

The tidy observation: **`copies` is doing two jobs with one structure.** It is
the visited set — "have I handled this node?" — *and* the lookup used to wire
edges — "what is this original's copy?". A separate `visited` set beside it
would be the same information stored twice, and keeping two structures in sync
is how the duplicate-node bug gets written.

## Register before recursing

Insert the copy *after* the recursion and a cycle coming back around finds
nothing, recurses again, and never bottoms out — the original bug, now with
extra steps. The self-loop case makes it undeniable:
`test_handles_a_self_loop` has a node whose own neighbour list contains itself,
so the lookup must succeed while the node is still being built.

This is the same ordering obligation as marking a cell before descending in
[find a word in a grid](../find-a-word-in-a-grid/notes.md). The difference is
the one worth carrying away:

| | mark means | lifetime | wrong choice gives |
|---|---|---|---|
| word search | "on the current path" | undone on the way out | a search that blocks itself |
| clone graph | "already copied" | permanent | infinite recursion |

Two bookkeeping steps that look identical in the code and are opposites in
intent. When a traversal misbehaves, asking which of these two you meant is
usually faster than reading the loop again.

## Key on identity, not value

```python
copies: dict[int, Node] = {}        # keyed by id(original)
```

Two distinct nodes may hold the same value — the prompt does not forbid it —
and a registry keyed on `node.value` silently merges them.
`test_handles_duplicate_values` has two different nodes both holding `7`.

Using `id()` is right here and worth one caution: it is only valid while the
objects are alive, which they are for the duration of the call. A dict keyed on
the nodes themselves would be the cleaner expression if `Node` were hashable by
identity, which by default it is.

## What "deep" means

```python
duplicate.neighbours = original.neighbours      # wrong, and passes shape checks
```

Every shape fingerprint matches, because the values and the edges are all
correct. The copy just happens to be wired into the original graph.
`test_shares_no_nodes_with_the_original` asserts the two node sets are
**disjoint** by identity, which is the only way to see it — and the same reason
[reverse a linked list](../reverse-a-linked-list/notes.md) has to assert
`result is nodes[-1]`.

## What to take away

**When a traversal needs memory, ask what the memory means.** "Seen on this
path" is backtracking and must be undone; "already processed" is memoisation
and must not be. The two are one line apart and the failures are nothing alike.

And the smaller lesson: when the visited set and a result lookup would be keyed
identically, **they are one structure**. Noticing that removes a whole class of
"the sets disagreed" bug.

# Add and Search a Word — the literals do the pruning

Revealed after grading. The problem is the classic one (LeetCode 211); the
wording above is ours. It is
[implement a trie](../implement-a-trie/notes.md) with one new query, and the
reason it is a separate kata is that the new query changes a *walk* into a
*search* — and shows exactly what the trie was buying you.

## Walk becomes search

```python
def matches(node, index):
    if index == len(pattern):
        return node.is_word
    character = pattern[index]
    if character == WILDCARD:
        return any(matches(child, index + 1) for child in node.children.values())
    child = node.children.get(character)
    return child is not None and matches(child, index + 1)
```

- At a **literal** there is at most one child to follow — a single path.
- At a **wildcard** there are as many branches as the node has children, and
  any one matching is enough.

So the cost is not uniform. A pattern with **no** wildcards costs
`O(len(pattern))`, unchanged from an ordinary lookup. Only the wildcards cost
branching, and only below the point where they appear.

**That asymmetry is the whole argument for the trie here.** A list of words
with `fnmatch` is three lines and costs `O(total characters)` for *every*
search, wildcards or not. `test_prunes_on_literal_characters` is the test that
separates them: a hundred thousand stored words and a thousand
literal-prefixed queries, which the scanning version does not finish.

## Length is enforced by the structure

Each step consumes exactly one pattern character and descends exactly one
level, so success requires the pattern to run out *at* a node that is a stored
word. `len(pattern) == len(word)` is never checked anywhere — it is a
consequence of the recursion's shape.

That is worth noticing because the alternative reading of `.` — matching zero
or many, as in a glob — would need a genuinely different recursion, one that
can stay at the same node while advancing the pattern. `test_requires_the_lengths_to_match`
pins the version we specified: `search("b.")` against three-letter words is
`False`.

## No backtracking marks, and why

Contrast with [find a word in a grid](../find-a-word-in-a-grid/notes.md), where
every step had to mark a cell and unmark it on the way out.

Here there is nothing to mark. Each step consumes a pattern character and moves
strictly **downward**, so the recursion cannot return to a node it is already
inside. The state that would need undoing does not exist.

The difference is the shape of what is being searched: **a grid is a graph with
cycles; a trie is a tree.** When a DFS runs over a tree, "visited" bookkeeping
is dead weight — and when it runs over a graph, leaving it out is an infinite
loop. Same recursion skeleton, and whether you need the marks is a property of
the structure, not of the algorithm.

That is the third time this distinction has come up — the permanent mark in
[clone a graph](../clone-a-graph/notes.md), the undone mark in the grid search,
and no mark at all here. Worth holding as a set.

## Branch across all children

`any(...)` over `node.children.values()`, not the first child. Whichever of
`"bad"` and `"cat"` is tried first fails for one of `".ad"` / `".at"`, so a
solution that commits to one child returns `False` for one of them.
`test_keeps_searching_after_a_failed_branch` is that pair.

Python's `any` short-circuits, so the first success stops the search — which is
the behaviour you want and costs nothing to get.

## What to take away

**Adding a query to a data structure can change its cost model without
changing its shape.** The trie here is byte-identical to the previous kata's;
only the search is new, and the new search is cheap exactly where the old one
was and expensive where the pattern is vague. Knowing *which* queries are cheap
is most of what it means to know a data structure — and it is the thing a
one-line `fnmatch` alternative silently gets wrong.

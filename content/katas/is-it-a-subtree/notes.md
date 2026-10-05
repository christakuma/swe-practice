# Is It a Subtree — two questions, two functions

Revealed after grading. The problem is the classic one (LeetCode 572); the
wording above is ours. It is the direct sequel to
[are two trees the same](../are-two-trees-the-same/notes.md), and it is here
to make one point: trying to answer both of its questions in a single
recursion is what makes it hard.

## The two questions

- **"Are these two trees identical?"** — a comparison that walks both trees in
  step and fails on the first disagreement.
- **"Does this tree contain that one?"** — a *search* that must be able to fail
  a match at one node and carry on looking elsewhere.

A single function comparing both trees in step cannot express the second,
because failing is how it returns, and the search needs failure to mean "try
the next node". So:

```python
def is_subtree(tree, candidate):
    if candidate is None:
        return True
    if tree is None:
        return False
    return (_same(tree, candidate)
            or is_subtree(tree.left, candidate)
            or is_subtree(tree.right, candidate))
```

`_same` is lifted wholesale from the previous kata. `O(n·m)` worst case,
`O(h)` stack.

**That is the transferable shape: "contains a match" is a search whose
predicate is a separate, total function.** The same split shows up in substring
search, in pattern matching, and in
[find a word in a grid](../find-a-word-in-a-grid/notes.md), where `search` from
each starting cell is the predicate and the `any(...)` over cells is the
search.

## Complete is the operative word

The one bug worth building tests around: a comparison that stops when the
**candidate** runs out.

```python
def _same_lenient(a, b):
    if b is None:
        return True              # <- the bug
    ...
```

This turns "contains this subtree" into "contains at least these nodes". Both
of these then come back `True` when the right answer is `False` — verified
against the broken version rather than assumed:

```
tree: 3(4(1, 2(0)), 5)     candidate: 4(1, 2)      extra child below the 2
tree: 1(2(4), 3)           candidate: 2            the 2 is not a leaf here
```

`test_rejects_a_near_match_with_an_extra_child` and
`test_rejects_a_single_node_that_is_not_a_leaf_in_the_tree` are those cases.

Note where the asymmetry lives: `_same` needs a base case that rejects
"exactly one is None" — the same load-bearing line as in the previous kata.
`is_subtree` needs the *opposite* for its candidate: `None` means success. Two
functions, two different conventions about emptiness, and merging them means
picking one and being wrong about the other half of the problem.

## Why the search has to keep going

`test_keeps_searching_after_a_failed_match` uses `1(2(4), 2)` looking for a
bare `2`. The first `2` reached has a child and cannot match; the second is a
leaf and does. A solution that commits to the first value match and then
reports its failure returns `False`.

This is the concrete reason the predicate must be **total** — it answers
"identical or not" about a specific pair and does not get a say in what happens
next. Predicates that try to steer the search are how backtracking bugs get
written.

## The better algorithm

Serialise both trees and ask whether one string contains the other:

```python
def serialise(root):
    if root is None:
        return "#"
    return f"({root.value}{serialise(root.left)}{serialise(root.right)})"
return serialise(candidate) in serialise(tree)
```

`O(n + m)` with a real substring search, against `O(n·m)` for the nested walk.

It only works if the serialisation is **unambiguous** — it must record absent
children, and the values must be delimited so that `12` cannot be read as `1`
followed by `2`. Which is precisely the lesson of
[encode and decode strings](../encode-and-decode-strings/notes.md): framing
that the payload can imitate is framing you cannot trust. A serialisation
without the `#` markers, or without the brackets, produces false positives that
are genuinely hard to find.

## What to take away

**When a problem is "find a thing satisfying P", write P first and alone.**
Keeping the predicate separate from the search gives you something you can test
in isolation, reuse — `_same` is a previous kata verbatim — and reason about
without holding the traversal in your head. Fusing them saves a function call
and costs you the ability to say what either half does.

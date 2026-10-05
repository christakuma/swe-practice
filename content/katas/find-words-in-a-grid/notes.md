# Find Words in a Grid — invert the loops

Revealed after grading. The problem is the classic one (LeetCode 212); the
wording above is ours. It is the capstone of three katas —
[find a word in a grid](../find-a-word-in-a-grid/notes.md) and
[implement a trie](../implement-a-trie/notes.md) composed — and the
composition, not either half, is the lesson.

## The obvious answer and why it is too slow

```python
return sorted({word for word in words if exists(board, word)})
```

Correct, and it repeats the same grid walk for every word sharing a prefix. A
word list is *mostly* shared prefixes, so almost all of that work is done
several times.

Measured on the test input — a 6×6 grid of a single letter and forty words
that are a 13-letter run of it followed by an absent letter, so every word
forces the full exponential exploration before failing:

| | time |
|---|---|
| grid searched once, carrying a trie | **0.8s** |
| single-word search, once per word | ~32s |

Against a 20-second limit. One `continue`-sized idea apart, as in
[longest consecutive run](../longest-consecutive-run/notes.md).

## The move

**Invert the loops.** Instead of *for each word, search the grid*, do *search
the grid once, carrying all the words at the same time*:

```python
def search(row, column, node):
    letter = board[row][column]
    child = node.children.get(letter)
    if child is None:
        return                      # no word continues this way: stop
    ...
    board[row][column] = VISITED
    for dr, dc in STEPS:
        search(row + dr, column + dc, child)
    board[row][column] = letter
```

The trie node is the "which words are still possible" state, and it costs one
dict lookup per step to maintain. Shared prefixes become shared work, and the
size of the word list stops multiplying the cost.

**That is the transferable shape: when an outer loop re-runs an expensive inner
search with slightly different parameters, look for a structure that carries
all the parameters at once.** The trie is doing for this grid search what a
prefix table does for multi-pattern string matching (Aho–Corasick is the same
idea with the search over a string instead of a grid).

## Two kinds of state, one needs undoing

The point worth carrying away from the whole trie/grid trio:

| state | undone? | why |
|---|---|---|
| the cell mark | **yes** | the grid is a graph with cycles; a path must not reuse a cell |
| the trie descent | **no** | the trie is a tree; `child` is passed down and the caller's `node` is untouched |

One search running over both structures at once, with opposite bookkeeping
requirements. Whether a DFS needs backtracking marks is **a property of the
structure, not the algorithm** — the same conclusion reached three different
ways: permanently in [clone a graph](../clone-a-graph/notes.md), undone in the
single-word grid search, and not at all in
[add and search a word](../add-and-search-a-word/notes.md).

## The prunings are what make it finish

Three, and each is a line:

**`child.word = None` after a hit.** Stops the same word being found again by
another path, which makes the result naturally duplicate-free — no `set`
needed. `test_returns_each_word_once` covers it.

**Deleting an exhausted child** — a node with no children and no word left —
shrinks the trie *as the search proceeds*. Later starting cells never
re-explore branches that can no longer produce anything, which is what keeps a
large word list from costing a large amount per cell. The data structure
getting smaller as it is used is unusual; compare path compression in
[count connected components](../count-connected-components/notes.md), which
flattens itself for the same kind of reason.

**Dropping words longer than the grid** before building the trie, which is
free and removes a family of hopeless branches.

## Recording a hit must not stop the search

A found word may be the prefix of another. `test_finds_a_word_that_is_a_prefix_of_another`
uses `["ab", "abd"]`: returning early after `"ab"` loses `"abd"`.

## On verifying it

Checked against the single-word search — the slow solution, used as an oracle —
over **380,100** (grid, word-list) pairs: every 1×2, 2×2 and 2×3 grid over two
letters, crossed with every one-, two- and three-word subset of the words up to
length four.

That is the right oracle precisely because it is the solution the kata forbids:
it shares no trie, no pruning and no mutation with the real answer, so
agreement is evidence rather than coincidence.

## What to take away

**Composing two solved problems introduces bugs in neither of them — only in
the seam.** Here the seam is the state: two structures traversed
simultaneously, one needing its marks undone and one not. Getting that right is
the whole exercise, and it is the thing neither parent kata could teach.

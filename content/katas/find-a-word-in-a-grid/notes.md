# Find a Word in a Grid — the mark has the lifetime of the path

Revealed after grading. The problem is the classic one (LeetCode 79); the
wording above is ours. It is the library's introduction to **backtracking**,
and the single idea worth taking from it is in the title: the bookkeeping that
makes backtracking work is scoped to the current path, not to the search.

## The shape

Depth-first search over a two-part state: where you are in the grid, and how
far through the word you are.

```python
def search(row, column, index):
    if index == len(word):
        return True
    if not in_bounds(row, column) or board[row][column] != word[index]:
        return False

    letter = board[row][column]
    board[row][column] = VISITED          # mark
    found = (search(row + 1, column, index + 1)
             or search(row - 1, column, index + 1)
             or search(row, column + 1, index + 1)
             or search(row, column - 1, index + 1))
    board[row][column] = letter           # unmark
    return found
```

A cell succeeds if its letter matches and **some** neighbour can spell the
rest, so the four calls combine with `or` — and Python's short-circuiting means
the first branch that works ends the search for free.

Worst case `O(m·n·4^L)` time for a word of length `L`, `O(L)` space for the
recursion.

## Two bugs, and they are not the same bug

**No marking at all.** `"ABCB"` on the example board returns `True`: the path
walks `A → B → C` and then steps back onto the `B` it came from. Every letter
is genuinely there; the path is not. This is the bug the prompt warns about and
`test_refuses_to_reuse_a_cell` catches.

**Marking permanently** — a `visited` set that is added to and never discarded.
This is the subtler one, and it fails in the *opposite* direction: it reports
`False` for words that are present. Once a dead-end exploration has marked a
cell, no later path can use it, so the answer depends on which starting cell
happened to be tried first.

The smallest grid that separates them:

```
A A        word = "AAAB"
A B
```

The only path is `(1,0) → (0,0) → (0,1) → (1,1)`. Starting at `(0,0)` instead
walks to `(0,1)` and strands the search — and with a permanent set, those two
cells are now spent, so the real path is never reachable. Correct answer
`True`; permanent-visited answer `False`.

**That case was found by running the buggy version against a brute-force
search over every 2×2 and 2×3 grid, not by thinking about it.** The first
counter-example written for this kata — a 3×3 ring of `A`s around a central
`B` — looked obviously discriminating on the page and the broken solution
passed it. Worth stating plainly, because it is the general risk with
adversarial tests: a counter-example you have not executed against the bug it
names is a guess.

## Mutating the board, and whether to

Writing a sentinel into the grid and restoring the letter on the way out is
`O(1)` extra space instead of `O(L)`, and the board is byte-identical by the
time the function returns.

It is still worth being uneasy about. It is not reentrant, two threads cannot
share the board, and a caller reading the grid mid-search sees corruption. The
`set` of coordinates — added before the recursion, discarded after — is the
same algorithm, costs `O(L)`, and is the better default in real code. The
mutation version is here because it makes the mark/unmark symmetry impossible
to miss: the restore is a *line*, not a method call.

Either way, `test_restores_the_board` checks the grid comes back unchanged on
both success and failure. Leaving the sentinel behind on the failing path is
the easy mistake — an early `return False` that skips the unwind.

## The pruning that is not an optimisation

```python
if len(word) > rows * columns:
    return False
```

A word longer than the grid has cells cannot fit. Without this, a long absent
word on a uniform board explores the full exponential space to learn nothing.
`test_searches_a_large_uniform_board_within_the_time_limit` is the input that
cares: an 8×8 grid of `A` and the word `"AAAAAAAAAAZ"`, where every cell
matches every letter and the final `Z` is nowhere.

Worth knowing the stronger version too: a character-count check. If the word
needs four `E`s and the board has three, no search is required. Cheap, `O(m·n)`,
and it rejects a large family of hopeless inputs before the recursion starts.

## What to take away

**Backtracking is DFS plus an undo.** The mark records "this is on the path I
am currently exploring" — which is a statement with a lifetime, and the undo is
what gives it one. Every problem in this family has the same skeleton: choose,
recurse, un-choose. Permutations, subsets, N-queens, Sudoku, combination sum.

When one of them misbehaves, the question to ask first is whether the state
being threaded through the recursion has the right *scope*. Too wide and you
block paths that should be open; too narrow and you permit paths that reuse
what they shouldn't.

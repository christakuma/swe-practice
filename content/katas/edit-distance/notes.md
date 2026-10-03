# Four cases, and three of them cost one

`distance[i][j]` is the edit distance between the first `i` characters of the
source and the first `j` of the target. Ask what the last edit was:

```
if source[i-1] == target[j-1]:
    distance[i][j] = distance[i-1][j-1]              # free
else:
    distance[i][j] = 1 + min(
        distance[i-1][j-1],   # replace source[i-1] with target[j-1]
        distance[i-1][j],     # delete source[i-1]
        distance[i][j-1],     # insert target[j-1]
    )
```

The three paid cases are exhaustive: any sequence of edits ends with one of
them. The free case is the one that does the work — it is why two long strings
that mostly match are cheap.

```
        ""  r  o  s
    ""   0  1  2  3
     h   1  1  2  3
     o   2  2  1  2
     r   3  2  2  2
     s   4  3  3  2
     e   5  4  4  3      -> 3
```

## The base cases are the edge-case handling

The first row is `0, 1, 2, 3, ...`: turning an empty string into j characters
costs j insertions. The first column is the same downwards: i deletions. Fill
both before the loop, and the body never needs a test for an empty input —
`edit_distance("", "abc")` is answered entirely by the initialised row.

That is the pattern worth taking away from table DP: **initialise the
degenerate edges correctly and the interesting case has no special cases.** A
loop body full of `if i == 0` is usually a table whose boundary was not set up.

## Two rows, and what it costs you

The recurrence reads only row `i-1` and the current row, so two rows suffice:
O(min(n, m)) space instead of O(n·m). On 300×300 that is 600 integers rather
than 90,000.

The price is that you can no longer say **what** the edits were. The sequence is
the path through the table, and discarding the table discards the path. Keeping
the full table and walking back from the bottom-right — each step choosing which
of the three predecessors was used — gives the actual list of edits.

Which is nearly always what the caller wanted: "three edits" is less useful than
"replace k with s, replace e with i, insert g". `difflib`, `git diff` and every
spell-checker keep the path.

## Variants, each a one-line change

| variant | change |
|---|---|
| Damerau-Levenshtein | a fourth case for transposition: `distance[i-2][j-2] + 1` |
| longest common subsequence | drop the replace case; count matches instead |
| weighted edits | replace the `1 +` with a per-operation cost |
| prefix matching (autocomplete) | take the minimum over the last **row**, not the corner |

The weighted version is how real spell-checkers work: a replacement between
keys adjacent on the keyboard costs less than one between distant keys, and
that single change makes "teh" → "the" cheaper than "teh" → "tea".

## On symmetry

Insertion and deletion are mirror images, so the distance is symmetric —
`edit_distance(a, b) == edit_distance(b, a)`. The suite checks it, because a
solution that handles only one direction (say, only deletions from the source)
passes several of the earlier tests. It is also a useful property in practice:
it means edit distance is a genuine metric, which is what lets it be used for
clustering and nearest-neighbour search.

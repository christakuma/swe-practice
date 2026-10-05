# Best Path Sum in a Tree — return one thing, record another

Revealed after grading. The problem is the classic one (LeetCode 124); the
wording above is ours. It is the hardest tree problem on the list, and the
difficulty is one specific thing: **the recursion's return value and the answer
it is computing are different quantities.** Everything else follows.

## Reframing: every path has a top

A path can wander up and then down, so enumerating paths is awkward. But every
path has exactly one **highest node** — the point where it turns. So instead of
enumerating paths, consider each node as the turning point:

> The best path turning at this node = best downward path into the left child
> + this node + best downward path into the right child.

Each path is the turn of exactly one node, so visiting every node considers
every path. Same move as centre-expansion in
[longest palindromic substring](../longest-palindromic-substring/notes.md):
find the canonical feature every candidate has, and enumerate that instead.

## The split

```python
def descend(node):
    if node is None:
        return 0
    left = max(descend(node.left), 0)
    right = max(descend(node.right), 0)
    best = max(best, node.value + left + right)   # record: the turn
    return node.value + max(left, right)          # return: straight down
```

`descend` **returns** the best path going straight *down*, because that is all a
parent can use — a parent extending into this subtree cannot also turn inside
it, or the path would visit a node twice. It **records** the best turn here,
which may use both children and is therefore useless to the parent.

Return the turning value instead and the parent builds an impossible path:
on `1(2(4,5), 3(6,7))` the answer inflates from **18 to 28**, double-counting
node 2 and node 3. Verified against that variant, not assumed.

**That is the pattern worth keeping: when a recursion's local answer is not
what its caller needs, it has to produce both — one by return, one by
side-channel.** A `nonlocal` accumulator is the usual side-channel; returning a
tuple `(best_down, best_anywhere)` is the pure alternative and is a little more
honest, since it makes the two quantities visible in the type.

## Two maxima with zero, meaning different things

This is the subtler trap, and the two are easy to conflate:

```python
left = max(descend(node.left), 0)     # "or take no child at all"
best = float("-inf")                  # NOT 0
```

`max(..., 0)` on a child is about **whether to extend**. A subtree whose best
downward path is negative should be skipped entirely — contributing nothing
beats contributing a loss — and zero is exactly "skip it".

`best` is about **which path wins**, and a path must contain at least one node.
An all-negative tree therefore has a negative answer. Seed `best` at `0` and
`[-2, -1, -3]` reports `0`, which is not the sum of any path in that tree.

Both lines look like "clamp at zero". One is a choice about structure, the
other would be a lie about the domain. `test_handles_an_all_negative_tree` is
the case; it is the same empty-versus-non-empty distinction as the seed in
[maximum product subarray](../maximum-product-subarray/notes.md), where
starting at the multiplicative identity `1` is wrong for the same reason.

## The float leak

`float("-inf")` is the natural seed and it makes the answer a float. `int(best)`
at the end is not cosmetic — a function declared to return `int` that sometimes
returns `-1.0` will pass every `==` test and fail the first `is` check or
serialisation. `test_returns_a_plain_integer` holds it.

The alternative is seeding with `root.value`, which is always a valid path sum
and keeps everything integral. Slightly better, slightly less obvious.

## On verifying this one

The reference was checked against a brute-force path enumerator — the tree
viewed as an undirected graph, every simple path walked — over **140,680
trees**: every binary tree shape up to five nodes, crossed with every value
assignment from `{-2, -1, 0, 1, 3}`.

That was worth the five minutes. Both of this kata's real bugs produce
*plausible numbers*, and the sign patterns that expose them are specific: the
zero-floor bug needs an all-negative subtree, and the return-versus-record bug
needs two children that are both positive. Picking those by hand means already
knowing the bugs — which is the thing the tests are supposed to establish, not
assume.

## What to take away

**Ask what the caller can actually use.** When a recursive helper's natural
local answer is richer than what composes upward, you have two quantities and
need to say so. Returning the wrong one is not a slip — it is a claim that the
parent can reuse a path that has already turned, and the resulting bug looks
like arithmetic rather than like a category error.

# The property is global; the obvious check is local

```python
# wrong
return root.left.value < root.value < root.right.value and ...
```

This accepts a tree that is not a search tree:

```
      5
     / \
    3   8
   / \
  1   6        6 is in 5's LEFT subtree, and 6 > 5
```

Every parent-child pair is in order: `6` is a legitimate right child of `3`, and
`3` is a legitimate left child of `5`. But `6` sits in the left subtree of `5`,
where everything must be below 5. The constraint is on **descendants**, and a
check that only looks one level down cannot see it.

That is the whole kata, and it is a useful instinct to build: when a property is
stated about a subtree, a per-node check is probably not enough.

## Carry the bounds down

Each node inherits an open interval it must lie in. Descending narrows it:

```
node        allowed range     why
----        -------------     ---
5           (none, none)      the root is unconstrained
3           (none, 5)         stepping left at 5 caps everything below at 5
1           (none, 3)         stepping left at 3 caps it again
6           (3, 5)            right of 3 raises the floor; 5's ceiling remains
                              -> 6 is not below 5, so the tree is rejected
8           (5, none)         stepping right at 5 raises the floor to 5
```

The ceiling set at `5` is what travels all the way down the left side, and it is
the thing a per-node check never has. Note that the floor and the ceiling come
from different ancestors: `6`'s floor is from its parent and its ceiling is from
its grandparent.

Two details:

- **No bounds at the root.** Seeding with `0` rejects every tree containing a
  negative value, and seeding with `float("-inf")` works while quietly changing
  the type of the comparison. `None` for "no bound" compares only values that
  are actually in the tree.
- **Strict comparisons**, because duplicates are disallowed here. Some
  definitions permit duplicates on one side; that is a specification question,
  and the answer changes `<=` to `<` in exactly one place. Decide it rather than
  discovering it.

## The other correct solution

An **in-order traversal of a search tree is sorted**. So:

```python
values = in_order(root)
return all(a < b for a, b in zip(values, values[1:]))
```

That is a genuinely different argument for the same conclusion, and it is often
the cleaner one to explain. Two caveats:

- it is O(n) extra space unless you track only the previous value as you go,
  which is the streaming version and the one to write
- `<` not `<=`, again — the sortedness has to be strict to catch duplicates,
  and `sorted(values) == values` does *not* catch them

Both solutions are O(n) time. The bounds version fails fast on a bad tree; the
in-order version has to reach the offending pair, which is usually the same
thing.

## Why anyone cares

The search tree property is what makes lookup O(h): at each node you can
discard a whole subtree. A tree that is *nearly* a search tree gives you a
lookup that is silently wrong rather than slow — it will confidently report that
a value is absent because it took the wrong branch. That is the kind of bug this
validation exists to catch, and it is why "every descendant" is the right
reading rather than a pedantic one.

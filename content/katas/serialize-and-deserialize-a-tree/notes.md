# Serialize and Deserialize a Tree — the absences are the data

Revealed after grading. The problem is the classic one (LeetCode 297); the
wording above is ours. It is the tree counterpart of
[encode and decode strings](../encode-and-decode-strings/notes.md), and the two
make the same point from different directions: **a format that cannot represent
its own edge cases cannot be decoded.**

## Why a traversal of the values is not enough

```python
def serialize(root):
    return ",".join(str(n.value) for n in preorder(root))     # loses the shape
```

Many different trees produce the same list of values. The smallest case:

```
   1            1
  /              \        both serialise to "1,2"
 2                2
```

So the string has to record something that a traversal of *present* nodes does
not — and what it is missing is precisely the **absences**.

```python
def visit(node):
    if node is None:
        parts.append("#")          # <- the whole design
        return
    parts.append(str(node.value))
    visit(node.left)
    visit(node.right)
```

That `"#"` is not padding or a convenience. It is the only thing in the string
that carries structure. `test_preserves_which_side_a_lone_child_is_on` asserts
the two trees above get *different* strings, which is a claim about the format
rather than about the round trip.

Same realisation as in [are two trees the same](../are-two-trees-the-same/notes.md),
where the comparison had to reject "exactly one is None" to mean "same shape".
Both problems turn on noticing that a missing child is information.

## Why pre-order

Pre-order puts a node **before** its children, which is exactly what a reader
needs: take a token, make the node, then fill its left and right from whatever
follows.

```python
def build():
    token = next(tokens)
    if token == "#":
        return None
    node = TreeNode(int(token))
    node.left = build()
    node.right = build()
    return node
```

In-order cannot be deserialised at all without extra information — the root is
somewhere in the middle and nothing says where, which is the whole difficulty
of [rebuild a tree from traversals](../rebuild-a-tree-from-traversals/notes.md)
and the reason that problem needs *two* traversals. Post-order works if you
read it backwards, building right children first. Level-order works with a
queue. Pre-order is the one where the reader's natural order is the writer's.

## The reader must share its position

```python
tokens = iter(data.split(","))
```

An iterator, not a fresh scan per call. The recursion needs "whatever comes
next" to be well defined across sibling calls — `build()` for the left child
consumes an unknown number of tokens, and the right child must resume exactly
where it stopped. Re-splitting or re-indexing from the start inside each call
either loses that or makes it quadratic.

This is the same obligation as `pre_start` in the rebuild kata: **a recursion
that consumes a stream needs the stream's position to be shared, not
recomputed.**

## Why a separator is safe here and not there

Worth being explicit, because the lesson in the string codec was that
separators cannot be trusted:

> A separator is sound exactly when the payload's alphabet excludes it.

Here the payloads are **integers**, and a decimal integer cannot contain a
comma. So `","` is a legitimate framing choice. In `encode-and-decode-strings`
the payloads were arbitrary strings, so no character was safe and length
prefixing was the answer.

The distinction is the point. "Use a separator" and "never use a separator" are
both wrong as rules; the question is always whether the payload can imitate the
framing.

## The marker must not be falsy

```python
if not token:        # or: if token == "0"
    return None
```

Using a falsy value as the absence marker makes a genuine `0` vanish.
`test_round_trips_zero` is that case — a small bug with a very quiet failure,
since the tree comes back shaped slightly wrong rather than raising.

Likewise the delimiter has to exist at all: without it, a `1` followed by a `2`
is indistinguishable from `12`, which `test_round_trips_multi_digit_values`
holds.

## What to take away

**Serialising a structure means serialising its holes.** Any format built from
"walk the thing and write what you find" will lose shape, because shape lives
in what you *didn't* find. The fix is always the same — write the absence down
— and it is the reason real formats have explicit nulls, explicit lengths and
explicit terminators rather than relying on what happens to be there.

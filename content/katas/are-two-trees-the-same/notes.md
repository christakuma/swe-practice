# Are Two Trees the Same — the base case that carries the meaning

Revealed after grading. The problem is the classic one (LeetCode 100); the
wording above is ours. The recursion is three lines. The reason it is worth
doing is that **one of its three base cases is the entire specification**, and
dropping it leaves a function that passes most tests and compares the wrong
thing.

## The move

The definition is the program:

```python
if first is None and second is None:
    return True
if first is None or second is None:
    return False
return (first.value == second.value
        and is_same_tree(first.left, second.left)
        and is_same_tree(first.right, second.right))
```

`O(n)` time, `O(h)` stack.

## The middle base case is the whole point

```python
if first is None or second is None:
    return False
```

This is what makes **shape** matter. Collapse it — treat a missing node as
matching anything, or return `True` as soon as either side runs out — and the
comparison never reaches a node to disagree about:

```
   1            1
  /              \      becomes "the same"
 2                2
```

Same values, different trees. `test_rejects_the_same_values_in_a_different_shape`
is that case, and every other test in the suite passes without the guard.

The lesson generalises past trees: **when comparing two recursive structures,
the interesting case is the one where they disagree about having run out.**
Equal-length comparison is easy; it is the asymmetric termination that encodes
"same shape", and it is exactly the case a hurried base case elides. Same
oversight as the missing length check in
[is it an anagram](../is-it-an-anagram/notes.md) — there, a short second string
sailed through for the same reason.

## Why not compare traversals

```python
def inorder(root):
    return inorder(root.left) + [root.value] + inorder(root.right) if root else []
return inorder(first) == inorder(second)
```

Wrong, and wrong in exactly the way above: a traversal that omits absent
children loses the shape. The two trees in the diagram both yield `[2, 1]`.

It becomes correct the moment the serialisation **records the absences**:

```python
def shape(root):
    return None if root is None else (root.value, shape(root.left), shape(root.right))
```

That is what the test suite uses as its oracle, and it is a genuinely good
solution — `O(n)` time, `O(n)` space to build the tuples, and it makes
"structurally equal" a value you can hash, cache or compare in bulk. The
recursive comparison is better when you only need the one answer, because the
`and`s short-circuit and nothing is allocated.

Worth knowing both, because the serialisation is what
[serialize and deserialize a tree](../serialize-and-deserialize-a-tree/notes.md)
is built on, and the reason it must record absences is the same reason here.

## On `first is second`

```python
if first is second:
    return True            # covers both-None, plus two refs to one tree
```

A real optimisation — and a bad opening line for a teaching solution, because
it makes the structural base case look like an identity case. Two distinct
trees that are equal is the normal input; two references to the same tree is
the rare one.

## What to take away

**The base cases of a recursion are where its specification lives.** The
recursive step here is obvious and nobody gets it wrong. Everything that makes
this function mean "same shape and same values" rather than "same values
somewhere" is in the three lines before it — and the one that does the work is
the one that looks like defensive boilerplate.

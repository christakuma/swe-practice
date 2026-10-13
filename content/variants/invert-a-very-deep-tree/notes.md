# The call stack was a list all along

Revealed after grading.

```python
def invert(root):
    if root is None:
        return None
    root.left, root.right = invert(root.right), invert(root.left)
    return root
```

That is the standard answer and there is nothing wrong with its logic. What
is wrong is where it keeps its to-do list. Each call that has not returned is
a frame on the interpreter's stack, and CPython allows about a thousand. A
balanced tree with a million nodes is twenty levels deep and never notices. A
chain of two thousand nodes fails.

So keep the list yourself:

```python
pending = [root] if root is not None else []
while pending:
    node = pending.pop()
    node.left, node.right = node.right, node.left
    pending.extend(child for child in (node.left, node.right) if child is not None)
```

The list lives on the heap, where the limit is memory.

## Why this one is easy to convert

Removing recursion is not always this painless. It is here because the work
at each node — swap two pointers — needs nothing from the children. There is
no result to wait for and combine, so no "come back to this node afterwards"
has to be recorded. Any order that visits every node works: stack, queue,
whatever.

A function like "height of a tree" is harder: the parent needs its children's
answers, so the explicit version has to visit each node twice or store
partial results. That is the real dividing line, and it is worth noticing
which side a problem is on before promising an iterative rewrite.

## About `sys.setrecursionlimit`

Raising the limit makes the recursive version pass, and on older Pythons
would crash the interpreter outright on a deep enough tree, since each Python
frame also consumed C stack. It is a setting for the whole process, changed
to suit one function. The explicit list has no such side effect.

## What the twist was testing

Reading the constraints. Nothing about the *problem* changed — only a number
in the small print — and that number invalidates the answer most people have
memorised. "How deep can the tree be?" is the question to ask before writing
any recursive tree function.

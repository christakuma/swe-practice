# Two pointers, and an argument for why they must meet

```python
slow = fast = head
while fast and fast.next_node:
    slow = slow.next_node
    fast = fast.next_node.next_node
    if slow is fast:
        return True
return False
```

**If the list ends**, the fast pointer reaches the end first and the loop exits.
**If it loops**, both pointers end up inside the loop and stay there. From then
on, the fast pointer gains exactly one position per step on the slow one, so the
gap between them shrinks by one each step — and a quantity that decreases by
exactly one cannot skip past zero. They meet.

That last sentence is the proof, and it is worth being able to give it. Three
steps at a time would *not* obviously work: the gap would shrink by two per
step, which can step over zero in a loop of odd length. It happens to still work
out, for reasons involving the loop length, and "it happens to work out" is a
bad place to be.

## Both guards, and why

```python
while fast is not None and fast.next_node is not None:
```

- `fast is not None` — an **odd**-length acyclic list puts the fast pointer
  exactly on the last node, whose `next_node` is `None`, so the next iteration
  starts with `fast` at `None`.
- `fast.next_node is not None` — an **even**-length one puts it one short, so
  `fast.next_node.next_node` would be the attribute access that raises.

Drop either and you get an `AttributeError` on half of all acyclic inputs. Which
is why the suite has one test for each parity rather than one for "no cycle":
they fail for different reasons.

## Identity, not equality

`slow is fast`, not `slow == fast`. The question is whether the two pointers are
at the **same node**, and two different nodes can hold the same value. The suite
tests a loop that re-enters the middle of the list specifically because it is the
shape where a value comparison gives a plausible wrong answer.

This is a good instinct generally: when a problem is about structure rather than
content, compare identity.

## Why bother, when a set works

A `set` of visited nodes is correct, obvious, and O(n) space. For a linked list
in memory, that is usually the right engineering answer.

Floyd's algorithm earns its place where the sequence is not something you can
store:

- the "list" is a disk or network structure too large to index
- the sequence is **generated**, not stored — `x = f(x)` repeatedly. This is how
  you find the cycle in a pseudorandom generator, and it is the core of
  Pollard's rho factorisation. There is no list to put in a set.
- memory is genuinely constrained

It is also the gateway to the follow-ups that a set cannot answer cheaply:

**Where does the loop start?** After the meeting, move one pointer back to the
head and advance both one step at a time; they meet at the entry. The reason is
arithmetic about the distances involved, and it is the part of this algorithm
that is genuinely surprising rather than merely clever.

**How long is the loop?** Keep one pointer still after they meet and walk the
other round until it comes back.

## Complexity

O(n) time: the slow pointer travels at most the length of the list plus the
length of the loop. O(1) space — two pointers, whatever the input size.

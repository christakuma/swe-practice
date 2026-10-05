# Contains a Duplicate — the answer you can give early

Revealed after grading. The problem is the classic one (LeetCode 217); the
wording above is ours. The hash-set move is the same one as in
[two sum](../two-sum/notes.md) and is not why this kata exists. It is here for
the early return, which is the only thing that distinguishes a good answer from
the one-liner everybody writes.

## The move you already know

```python
seen = set()
for value in numbers:
    if value in seen:
        return True
    seen.add(value)
return False
```

"Have I seen this before?" is a membership question. A list answers it in
linear time, so asking once per element is `O(n²)`; a set answers it in
constant time, so one pass does it. Check before inserting, or every element
finds itself.

## Why the one-liner is banned

```python
return len(set(numbers)) != len(numbers)
```

It is correct, it is `O(n)`, and it is the version you should usually ship. It
is banned here because of what it cannot do:

| | one-liner | early-return loop |
|---|---|---|
| worst case | `O(n)` time, `O(n)` space | `O(n)` time, `O(n)` space |
| `[1, 1, ...a million more]` | `O(n)` time, `O(n)` space | **`O(1)`** |

Identical asymptotics, and one of them answers a question about a
billion-element list by looking at two elements. **Asymptotic notation
describes the worst case, and the worst case is not the only case you are paid
for.** An existential question — *does any* element satisfy this — is decided
by the first witness, and a formulation that computes a complete summary before
comparing it has thrown that away.

Same reason `any(...)` beats `len([x for x in xs if p(x)]) > 0`, and `in` beats
building an index you use once.

## How the tests check it

You cannot observe an early return from outside — a plain list does not record
how much of it was read. So the suite hands the solution a `list` subclass that
does:

```python
class Tripwire(list[int]):
    def __iter__(self):
        for index, value in enumerate(super().__iter__()):
            if index >= self.limit:
                raise AssertionError(...)
            yield value
```

It is still a `list`, so nothing about the interface changes, and iterating it
past the point where the answer was knowable fails loudly. Verified against
both rejected solutions: the `len(set(...))` version and the sort-and-compare
version each trip it on `[4, 4, 9, 9, 9]` with a limit of two.

**That technique is worth stealing.** When a requirement is about *what the
code does not do* — does not read more than it needs, does not call the
expensive dependency twice, does not touch the network — an instrumented
stand-in is usually the only way to assert it. A test that can only see return
values cannot see effort.

## Sorting, and the question it actually answers

```python
numbers.sort()
return any(a == b for a, b in zip(numbers, numbers[1:]))
```

Equal values become adjacent, so one pass over neighbours finds them. `O(n log n)`
time, `O(1)` extra space if you are allowed to mutate the caller's list — and
you usually are not, so copying gives the space straight back.

It also cannot return early, by construction: nothing can be concluded until
the sort finishes. So it fails this kata, and it is the right answer to a
different question — *what if memory, not time, is the binding constraint?*
Both are worth having. Reaching for the set automatically is a different
failure from never reaching for it.

## What to take away

The set is routine. The two things that are not:

**An existential question is answered by its first witness.** Build the habit
of returning the moment you know, rather than computing a complete answer and
then asking it a question.

**Tests that check for restraint need help.** Returning the right value is the
easy half; doing so without reading, allocating or calling more than necessary
is the half that needs an instrumented input to see.

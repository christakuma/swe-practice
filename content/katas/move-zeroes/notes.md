# Two pointers, one of which is a write cursor

The pattern is "read with one index, write with another, and keep an invariant
about everything behind the write index". Here the invariant is: *positions
`0..write-1` hold the non-zero elements seen so far, in their original order.*

```
[0, 1, 0, 3, 12]
 r                write=0   zero, skip
    r             write=0   1  -> position 0, write=1
       r          write=1   zero, skip
          r       write=1   3  -> position 1, write=2
             r    write=2   12 -> position 2, write=3
[1, 3, 12, 3, 12]           then fill from 3: [1, 3, 12, 0, 0]
```

The second loop is not optional tidying. After the first pass, positions from
`write` onwards still hold stale copies — `3` and `12` above appear twice —
because copying forward never cleared anything.

## The variant that loses the order

```python
# swap each zero with the last unprocessed element
```

Fast, in place, and it fails `[1, 0, 3, 0, 4]` → `[1, 4, 3, 0, 0]`. The task
says *keeping the original relative order*, which is the word "stable", and it
is the constraint that rules out the whole family of swap-with-the-end
partitions. Worth noticing when a problem says it, because the stable version is
usually a little more work.

The swap version that **does** keep order is this one with `swap` instead of
`copy`:

```python
numbers[write], numbers[index] = numbers[index], numbers[write]
```

Same invariant, no second loop, twice the writes. Both are standard; the copy
version is easier to be certain about, and the swap version is what you want if
writes are expensive (flash memory, say) because it never writes a zero it does
not have to.

## What makes it quadratic

```python
for index, value in enumerate(numbers):
    if value == 0:
        numbers.pop(index)
        numbers.append(0)
```

Two problems. `list.pop(index)` shifts every element after it, so n zeros make
it O(n²) — and mutating a list while enumerating it skips elements, so it is
also wrong. The long test case fails on time; a careful reading fails it on
correctness first.

## The generalisation

This is **stable partition**: rearrange so everything satisfying a predicate
comes first, order preserved. The same code with `if predicate(numbers[index])`
solves "move all the odd numbers to the front", "compact a list in place",
"remove deleted records from a buffer". It is also exactly what
`[x for x in xs if p(x)] + [x for x in xs if not p(x)]` does, in O(1) space
instead of O(n), which is the only reason to write the loop.

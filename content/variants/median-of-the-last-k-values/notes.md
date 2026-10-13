# Heaps cannot let go

Revealed after grading. This is "Sliding Window Median" (LeetCode 480).

The standard solution keeps a max-heap of the lower half and a min-heap of
the upper half; the median sits at the tops. It is perfect for a stream that
only grows. A heap knows its smallest element and nothing about where any
other element is, so "remove the value that arrived a thousand adds ago" is
the one operation it does not have.

A window needs two orders at once:

- **arrival order**, to know which value leaves;
- **sorted order**, to find the middle.

## The sorted list

Keep both, as two structures holding the same values:

```python
self._arrivals.append(value)
insort(self._ordered, value)
if len(self._arrivals) > self._size:
    leaving = self._arrivals.popleft()
    del self._ordered[bisect_left(self._ordered, leaving)]
```

Binary search finds the place; the list shifts to make or close the gap.
That shift is `O(k)`, but it is one `memmove` of a small array, and for
windows up to tens of thousands it comfortably beats cleverer structures in
Python. It is also the version you can write correctly in an interview.

`bisect_left` matters with duplicates: it lands on *a* copy of the departing
value and deletes exactly one. `list.remove(value)` would also work, at the
cost of a linear search.

## The heap version

Keep the two heaps, and delete lazily. When a value leaves the window, record
that it is owed a removal (a counter per value) and adjust which half is
considered larger. Whenever a heap's top is a value with a removal owed, pop
it then. Sizes have to be tracked separately from `len(heap)`, since the
heaps now contain ghosts. It is `O(log k)` per operation and about four times
the code, nearly all of it bookkeeping about balance.

## What the twist was testing

Knowing what a data structure cannot do. The two-heap median is a celebrated
trick, and the natural reaction to "now make it a window" is to try to bend
it. The better reaction is to list the operations the new problem needs —
insert, delete-by-value, find-middle — and ask which structure offers all
three.

# Keep only what could still matter

Revealed after grading. This is "Kth Largest Element in a Stream"
(LeetCode 703).

The median needed two heaps, because the middle moves in both directions as
values arrive. The kth largest only ever moves one way — up — and that makes
it a one-heap problem.

```python
if len(self._largest) < self._k:
    heapq.heappush(self._largest, value)
else:
    heapq.heappushpop(self._largest, value)
return self._largest[0] if len(self._largest) == self._k else None
```

**A min-heap for the largest values.** It feels backwards and is the whole
idea: of the k largest, the one to report — and the one to evict — is the
*smallest*, and a min-heap keeps exactly that on top.

Everything below the top k is discarded and never needed again. That is why
the memory is `O(k)` rather than `O(n)`, and why this works on a stream too
long to store.

"Which values can I throw away for ever?" is the question that turns many
streaming problems from impossible to easy.

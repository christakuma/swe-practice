# The same two pointers, started from the other end

Revealed after grading. A mirror image of "Move Zeroes" (LeetCode 283).

Nothing about the idea changes: one index reads, one writes, and the write
index only advances when something worth keeping is found. What changes is the
direction, and the direction matters for a reason worth being able to state.

```python
write = len(numbers) - 1
for read in range(len(numbers) - 1, -1, -1):
    if numbers[read] != 0:
        numbers[write] = numbers[read]
        write -= 1
```

**Read from the end you are packing towards.** Packing to the back while
reading from the front would overwrite values that have not been read yet, and
would reverse the ones it did manage to keep. Reading backwards, the read
index is always at or ahead of the write index — in the direction of travel —
so every value is copied before its slot is reused.

That is the general rule for any in-place compaction, and it is the same rule
`memmove` follows when the source and destination overlap: copy in the
direction that does not trample what you still need.

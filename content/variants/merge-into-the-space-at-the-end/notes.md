# Write where nothing is waiting to be read

Revealed after grading. This is "Merge Sorted Array" (LeetCode 88).

Merging linked lists is about relinking nodes; nothing is ever overwritten.
Arrays are different. Each write lands *on* something, and the whole problem
is making sure that something was not still needed.

The familiar merge walks both inputs from the front and writes to the front
of the output. Here the output is `first` itself:

```
first:  [4, 5, 6, _, _, _]     second: [1, 2, 3]
write 1 -> first[0]            ... and the 4 is gone
```

## Go the other way

The spare room is at the **end**, so that is where writing is safe. And a
merge works just as well backwards — largest first:

```python
while other >= 0:
    if read >= 0 and first[read] > second[other]:
        first[write] = first[read]; read -= 1
    else:
        first[write] = second[other]; other -= 1
    write -= 1
```

Why it never overwrites an unread value: `write - read` is always the number
of values of `second` not yet placed. While any remain, the write position is
strictly ahead of the read position. When none remain, the loop has ended.

## The loop condition

Run until **`second`** is exhausted, not until either is.

- `second` runs out first: the rest of `first` is already in position.
  Nothing to do.
- `first` runs out first: the rest of `second` still has to be copied down.
  `while read >= 0 and other >= 0` forgets it, and `[]` merged with `[3]`
  stays as junk.

## What the twist was testing

"Which direction is safe?" It is the question behind every in-place array
algorithm — `memmove` asks it, so does shifting elements to insert one, so
does removing duplicates. The rule is always the same: write towards where
the free space is, so that the write pointer runs ahead of nothing it needs.

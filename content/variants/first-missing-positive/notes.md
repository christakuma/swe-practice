# The list is the hash set

Revealed after grading. This is "First Missing Positive" (LeetCode 41).

The standard problem promises `n` distinct values from `0..n`, and the answer
falls out of arithmetic: XOR or sum what should be there against what is.
Every part of that promise is gone here. Values repeat, most of them are
irrelevant, and there is no range to compare against.

## The observation

The answer is between `1` and `n + 1`. It can only be `n + 1` if the list is
exactly `1..n`; anything else leaves a gap lower down. So values outside
`1..n` are noise, and for the ones inside there are `n` values and `n`
positions.

That is a hash table with a perfect hash: **value `v` goes at index
`v - 1`**.

```python
for position in range(size):
    while True:
        value = numbers[position]
        if not 1 <= value <= size or numbers[value - 1] == value:
            break
        numbers[position], numbers[value - 1] = numbers[value - 1], value
```

Then the first index `i` not holding `i + 1` is the answer.

## The three bugs

- **`if` instead of `while`.** The swap brings a stranger to this position,
  and it may need to go home too. `[2, 3, 1]` needs two swaps at index 0.
- **Testing `numbers[position] != position + 1`** to decide whether to swap.
  With a duplicate — `[1, 1]` — the second 1 is not at home, its home holds a
  1, and the swap changes nothing, for ever. Test the *destination*.
- **Swapping in the wrong order.** `numbers[i], numbers[numbers[i] - 1] = ...`
  assigns `numbers[i]` first and then uses the new value to compute the
  second index. Read the value into a variable.

It looks quadratic and is not: every swap puts one value in its final place,
and a value in its final place is never moved again, so there are at most `n`
swaps.

## What the twist was testing

Whether "use `O(1)` space" makes you look at what you were already given. The
other well-known answer — mark presence by negating the value at an index —
is the same idea: the input is `n` writable cells, and `n` cells is exactly
enough.

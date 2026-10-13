# Four cases, three reflections

Revealed after grading. "Rotate Image" (LeetCode 48), generalised.

## There are only four rotations

Four quarter turns bring the matrix back, so the count only matters modulo
4:

```python
turns %= 4
```

In Python that one line also handles direction. `-1 % 4` is `3`: one turn
anticlockwise is three clockwise, and the remainder comes out non-negative
because Python's `%` follows the sign of the divisor. In C or Java `-1 % 4`
is `-1`, and you would write `((turns % 4) + 4) % 4`.

So: nothing, clockwise, half turn, anticlockwise.

## Every rotation is two reflections

You already know one of these — clockwise is *transpose, then reverse each
row*. The full set, using three reflections:

| rotation | reflections |
|---|---|
| clockwise | transpose, then flip left-to-right |
| anticlockwise | transpose, then flip top-to-bottom |
| half turn | flip left-to-right, then flip top-to-bottom |

Three tiny loops, each of which obviously does what it says, combined three
ways.

The alternative — apply the clockwise turn `turns % 4` times — is also
correct, and at most three times the work. It is a perfectly good answer.
The reflections are worth knowing because they make the half turn fall out
with no transpose at all, and because they are the reason the standard trick
works in the first place.

## In place, exactly

A top-to-bottom flip is tempting to write as

```python
matrix.reverse()
```

which gives the right *values* and moves the row *objects*: the caller's
first row is now at the bottom. Whether that counts as "in place" is a
question worth asking in an interview. Here it does not, and the flip swaps
values between rows instead:

```python
for top in range(size // 2):
    upper, lower = matrix[top], matrix[size - 1 - top]
    for column in range(size):
        upper[column], lower[column] = lower[column], upper[column]
```

## What the twist was testing

Generalising without multiplying work. "Rotate by `turns`" invites a loop
that runs `turns` times, and `turns` is a thousand million. The first move
is to notice the operation has a period; the second is to see that the four
remaining cases are not four pieces of code but three small ones composed.
Spotting the period of an operation before looping over it is the same
reflex as `k % length` when rotating a list.

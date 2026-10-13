# The recurrence counts choices now, not possibilities

Revealed after grading. This is "Decode Ways II" (LeetCode 639), without the
modulus — Python does not need one.

The standard recurrence is

```
ways(i) = [last char can stand alone] * ways(i-1)
        + [last two form a letter]    * ways(i-2)
```

where each bracket is 0 or 1. The wildcard changes nothing about the shape.
The brackets become *counts*: how many letters the last character could be,
and how many the last two could be.

| last two | read together |
|---|---|
| digit, digit | 1 if 10..26, else 0 |
| `*`, digit `d` | 2 if `d <= 6` (1d and 2d), else 1 (only 1d) |
| `1`, `*` | 9 (11..19) |
| `2`, `*` | 6 (21..26) |
| other digit, `*` | 0 |
| `*`, `*` | 15 (11..19 and 21..26) |

That table is the problem. The loop around it is the one you already wrote.

## The numbers people get wrong

- **`**` together is 15.** Not 26: there are no zeros, so 10 and 20 are out,
  and nothing below 11 is two digits. Not 18: `2*` stops at 26.
- **`*` before a digit above 6 is 1, not 2.** `27` is not a letter.
- **`*0` is 2**, and both come from the "together" case. The zero cannot
  stand alone, so the star is forced to be 1 or 2.

## What the twist was testing

Whether the standard solution was held as a recurrence or as a pair of `if`
statements. `if valid: ways += previous` cannot be extended to "nine ways";
`ways = count * previous` extends without being touched. Writing the
yes-or-no version as a multiplication by 0 or 1 is the same code and a much
better starting point.

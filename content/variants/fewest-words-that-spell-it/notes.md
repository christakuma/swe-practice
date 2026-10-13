# Booleans become numbers; the table stays

Revealed after grading.

Word break asks whether a prefix can be spelled. Counting ways asks how many
spellings it has. This asks for the cheapest. All three fill the same table
in the same order, and differ in what an entry holds and how entries
combine:

| question | entry | combine | "impossible" |
|---|---|---|---|
| can it be split? | bool | `or` | `False` |
| how many ways? | int | `+` | `0` |
| fewest words? | number | `min(..., x + 1)` | infinity |

```python
if text[end - size:end] in known:
    fewest[end] = min(fewest[end], fewest[end - size] + 1)
```

## Why greedy fails, twice

*Take the longest word that fits, repeat.*

- It can be **suboptimal**: `"abcdefg"` with `abcd, abc, defg, e, f, g`.
  Greedy takes `abcd` and is left with three single letters; `abc` + `defg`
  is two.
- It can **fail to find any split**: `"abcd"` with `abc, ab, cd`. Greedy
  takes `abc` and is stuck with `d`.

A longer first word is not better; it just leaves a different remainder, and
you cannot judge a remainder without solving it. That is the definition of
needing a table.

## The sentinel

An unspellable prefix has to stay unspellable. With `-1` as the marker,
`-1 + 1 = 0` — a prefix that cannot be spelled suddenly costs nothing, and
everything built on it looks cheap. Infinity is the value that survives
`+ 1` and loses every `min`. Convert to `-1` once, at the return.

## What the twist was testing

Seeing a dynamic programme as a recurrence with a pluggable operation. Once
"can it be done", "how many ways" and "what is the best" are recognised as
one table under three operators, a follow-up in this family is a change to
one line and one initial value.

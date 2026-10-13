# Eight neighbours instead of four

Revealed after grading. The 8-connected form of "Flood Fill" (LeetCode 733).

Only the neighbour list changes:

```python
for dy in (-1, 0, 1):
    for dx in (-1, 0, 1):
```

It is worth generating the offsets rather than typing eight pairs — the pair
that gets mistyped is always one of the diagonals, and the result is a fill
that leaks in three diagonal directions and not the fourth.

"Connected" always needs a definition. Four-way and eight-way are both
standard, they give different answers on the same grid, and a problem
statement that does not say which is one to ask about.

# The complement of a union

Revealed after grading. A follow-up to "Pacific Atlantic Water Flow"
(LeetCode 417).

The standard solution runs two backward searches and intersects them: cells
that drain to one ocean *and* the other. This one wants the cells that drain
to no ocean, and the tempting answer is "everything that is not in the
intersection" — which is the cells that fail to reach *both*, a much larger
set that includes every cell reaching just one.

```
both      =  A and B
neither   =  not (A or B)        <- this problem
not both  =  not (A and B)       <- the tempting wrong answer
```

Since only the union matters, the two oceans do not need separate searches:

```python
if y in (0, rows - 1) or x in (0, columns - 1)
```

seeds a single search from every edge.

When a follow-up negates a condition, write the logic out. "Not both" and
"neither" differ by De Morgan's law, and the difference is most of the grid.

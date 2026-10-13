# The loop the other way round

Revealed after grading. The unbounded knapsack, sibling of the 0/1 version.

```python
for weight, value in items:
    for room in range(weight, capacity + 1):      # upwards
        best[room] = max(best[room], best[room - weight] + value)
```

The standard table walks `room` **downwards**, and the notes there explain
why: going upwards lets `best[room - weight]` already contain the current
item, so it gets used twice. That was the bug. Here it is the feature.

So one array, two problems, and the only difference is the direction of the
inner loop. If you can say why each direction does what it does, you
understand the table; if the two versions are two memorised recipes, the
first unfamiliar variant — each item at most twice, say — will not yield.

Greedy by value per weight still fails, for the same reason as before: the
capacity may not divide evenly, and the leftover room is worth filling with
something less efficient.

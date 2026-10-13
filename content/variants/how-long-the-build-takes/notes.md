# The longest path through the build

Revealed after grading. This is the critical path method; LeetCode's
"Parallel Courses III" (2050) is the same problem.

A topological order answers "what order *can* things happen in?". With
durations and unlimited parallelism the question becomes "when does each
thing happen?", and it has a one-line answer:

```
finish(task) = duration(task) + max(finish(d) for d in its dependencies)
```

A task starts when its **slowest** dependency is done. The build ends when
the last task does.

That recurrence needs every dependency's finish before the task's own, which
is exactly what processing in topological order guarantees. So the solution
is Kahn's algorithm with a number riding along:

```python
finish = ready_at[name] + durations[name]
for dependant in dependants[name]:
    ready_at[dependant] = max(ready_at[dependant], finish)
```

and cycle detection comes free, as before: if not every task came off the
queue, the rest are waiting on each other.

## What it is not

- **Not the sum.** That is one worker doing everything in sequence.
- **Not rounds.** Grouping tasks into parallel rounds and adding up the
  slowest task of each round overcounts: a slow task in round one need not
  delay a round-two task that does not depend on it.
- **Not the chain with the most tasks.** Three one-minute steps in a row
  finish before a single ten-minute step.

The answer is the *longest path* in the dependency graph, weighted by
duration — the "critical path". Tasks on it have no slack; shortening any
other task changes nothing.

## What the twist was testing

That a topological order is a means, not an end. It is the order in which a
recurrence over a DAG can be evaluated, and almost every practical use of it
is carrying something along: finish times here, counts of paths, shortest
and longest distances, the round number in "build in rounds". The sort
itself is rarely the answer anyone wanted.

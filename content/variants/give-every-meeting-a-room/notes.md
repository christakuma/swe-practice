# Two orders, two heaps

Revealed after grading. LeetCode's "Meeting Rooms III" (2402) uses the same
booking rule.

Counting rooms needs one heap of end times, and the answer is how large it
gets. The heap never knows which room an end time belongs to, because the
question never asked.

Asking *which room* looks like a small addition — store `(end, room)` — and
then the obvious code is wrong:

```python
if busy and busy[0][0] <= start:
    _, room = heapq.heappop(busy)      # the room that emptied first
```

That is the room that has been free **longest**, and the rule is the room
with the **lowest number**. They differ as soon as two rooms are empty at
once: room 2 empties at 3, room 1 empties at 4, a meeting arrives at 5. The
heap offers room 2. The answer is room 1.

There are two orderings in the problem — *when does a room empty* and *which
empty room is lowest* — and one heap can only keep one of them. So:

```python
while busy and busy[0][0] <= start:           # everything that has emptied
    heapq.heappush(free, heapq.heappop(busy)[1])
room = heapq.heappop(free) if free else new_room()
```

`while`, not `if`: all the emptied rooms have to reach the free heap before
the lowest can be chosen.

## The other detail

Sorting the meetings loses their positions, and the answer is wanted in input
order. Sort the *positions* by start time instead and write each result back
through its position. A stable sort keeps equal starts in input order, which
the booking rule needs.

## What the twist was testing

Noticing that a data structure was answering a slightly different question
than the one being asked. The min-heap of end times is so strongly associated
with this problem that it is easy to keep using it past the point where its
ordering is the one you want.

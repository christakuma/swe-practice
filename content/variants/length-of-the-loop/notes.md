# Once you are inside, just walk round

Revealed after grading.

Floyd's two pointers answer a yes-or-no question, and the standard problem
stops the moment they meet. But the meeting is more than a "yes": both
pointers are now standing on a node that is **in** the cycle. Finding such a
node was the hard part. Measuring the cycle from it is a walk:

```python
length = 1
walker = slow.next_node
while walker is not slow:
    walker = walker.next_node
    length += 1
```

## What the meeting does not tell you

It is tempting to count steps during the chase and return that. When they
meet, slow has taken `s` steps and fast `2s`, so the extra `s` is a whole
number of laps: `s` is a **multiple** of the cycle length. With no lead-in it
is exactly one lap, which is why the shortcut passes the easy tests. With
nine nodes leading into a cycle of two, they meet after ten steps.

The distance from the head to the meeting point is no better: that includes
the lead-in.

## Three questions, one walk

- *Is there a cycle?* — do they meet.
- *How long is it?* — walk round from the meeting point.
- *Where does it begin?* — restart one pointer at the head and step both
  together.

Each later question starts from where the first one finished. Knowing the
length gives another route to the third answer too: put one pointer `length`
steps ahead of the other and advance both; they meet at the entrance.

## What the twist was testing

Whether the algorithm was understood as producing a *position* rather than a
boolean. The standard solution throws that position away, and nothing in its
tests tells you it was worth keeping.

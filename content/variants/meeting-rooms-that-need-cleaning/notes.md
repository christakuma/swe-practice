# A gap is just a longer meeting

Revealed after grading. "Meeting Rooms II" (LeetCode 253) with a buffer, the
way a booking system actually has one.

```python
if ends and ends[0] + gap <= start:
```

That is the one changed line. A room that must be cleaned until `end + gap` is
occupied until `end + gap` from the point of view of whoever wants it next, so
the problem is the standard one with every meeting stretched by `gap`.

It is worth doing rather than just saying because of *where* the stretch goes.
Adding `gap` to the stored end times works too. Adding it to the start, or to
both, or using `<` so that a room ready exactly on time is refused, are the
ways this goes wrong — and each one passes every test that has no two
meetings exactly `gap` apart.

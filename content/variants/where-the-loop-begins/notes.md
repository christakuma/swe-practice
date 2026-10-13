# Where they meet is not where it starts — but it tells you

Revealed after grading. This is "Linked List Cycle II" (LeetCode 142).

Detecting a cycle needs the tortoise and the hare and nothing else. Finding
where it *begins* looks as though it needs memory — you have to recognise a
node you have seen before — and the pleasure of this problem is that it does
not.

## The arithmetic

Let `a` be the number of steps from the head to the first node of the cycle,
and `b` the further steps to the place the two pointers meet. When they meet:

- slow has walked `a + b`
- fast has walked `2(a + b)`, and is at the same node

So the extra `a + b` that fast walked is a whole number of laps of the cycle.
Now stand at the meeting point, `b` steps into the cycle. Walk `a` more: that
is `a + b` steps from the cycle's start in total — a whole number of laps —
which puts you exactly back **at the start**.

And `a` is also how far the head is from the start. So:

```python
probe = head
while probe is not slow:
    probe = probe.next_node
    slow = slow.next_node
return probe
```

Two pointers, one step at a time, one from the head and one from the meeting
point. They cannot help meeting at the first node of the cycle.

## What the twist was testing

That the first phase was understood rather than memorised. "Slow and fast
meet if there is a loop" is a fact you can recite; why they meet *where* they
do is the part that was always there and that the yes-or-no question never
asked about.

It is also a test of `is`. The answer is a node, the values tell you nothing,
and comparing with `==` or returning `node.value` both look fine on a list
whose values happen to be distinct.

# A queue that grows is a latency bug with no error message

## The arithmetic

A queue's length changes by **arrivals minus completions**, every second.
At 1,000 uploads a second and 800 thumbnails, it grows by 200 a second,
720,000 an hour, and it does so silently: every upload is accepted, every
job succeeds, every worker is busy and healthy. The only thing wrong is
time, and nobody was measuring it.

Two numbers people mix up:

- **How long a new job waits** is what is in front of it divided by how
  fast the front moves: 1,800,000 / 800 = 37.5 minutes. What arrives after
  it is behind it and does not matter.
- **When the queue is empty** depends on both rates: it drains at 800 - 300
  = 500 a second, so an hour. A queue that is "draining" can still be
  making everyone wait for the better part of an hour.

## Why unbounded is the bug

A queue exists to absorb **bursts**: arrivals briefly faster than service,
smoothed out once they pass. A sustained rate above capacity is not a
burst, and an unbounded queue absorbs it anyway, by converting overload
into delay that grows without limit. Nothing fails, so nothing alerts, and
the system degrades in the one dimension monitoring usually ignores.

A bound turns the hidden failure into a visible one: when the queue is
full, the producer finds out.

## Backpressure and shedding

What the producer does when it finds out is the design decision:

- **Backpressure**: slow the producer down or ask it to come back later
  (block, 429 with `Retry-After`, a "processing" state the client polls).
  Nothing is lost, and the delay is bounded and visible.
- **Load shedding**: refuse or drop work, ideally the least valuable, when
  saving everything would mean serving nothing well.

Here the photo must not be lost and the thumbnail may be late, so store the
photo, defer the thumbnail with a bound on how many may wait, and tell the
client. What does not help: a bigger bound (a longer delay), or a second
queue (the same queue, longer).

## Alert on delay and on rates, not on activity

The age of the oldest job waiting measures what users feel. Arrivals above
completions for ten minutes measures the cause before the delay is large.
Worker CPU and job failures look identical on a good day and a bad one,
and "queue not empty" pages on every burst. Little's law joins the two
views: queue length is arrival rate times time spent waiting, so a queue
that is twice as long at the same rate is a wait twice as long.

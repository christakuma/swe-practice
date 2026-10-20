# Read latency as a distribution, and capacity as a rate

## Percentiles say what the mean hides

p99 = 410 ms is a statement about requests: 99% finished in 410 ms or less,
and 1% took longer. Against an SLO of "99% under 300 ms", p99 is the number
to compare, and 410 > 300 means the SLO is missed, by roughly 12,000
requests last hour. The mean is the wrong number for two reasons. It is
dragged around by a few extreme requests, and it cannot say *how many*
requests were slow, which is the only thing the SLO asks.

## Fan-out multiplies the tail

A page that waits for five independent calls is fast only if all five are.
If each is slow 1% of the time, the page is slow 1 − 0.99⁵ ≈ 4.9% of the
time. At 100 calls it is 63%. This is the argument of Dean and Barroso's
*The Tail at Scale*: the more a request fans out, the further into the tail
each backend has to be good, so a backend's p99.9 becomes its users' p90.

## Little's law, and the cliff

Concurrency = throughput × time in system. A pool of 20 connections, each
held 50 ms, completes at most 20 ÷ 0.05 = **400 queries a second**. Below
that, waits are short and random. Above it, the excess queues up and nothing
drains it: at 450 a second the queue grows by 50 every second, and the wait
grows with it until the load drops or the pool's timeout fails people. Near
capacity, latency does not degrade gently, which is why capacity is planned
with headroom and why load shedding (refusing early) beats queueing forever.

## Aggregating percentiles

Percentiles do not average, and the maximum of per-instance p99s is only a
bound. To get a service-wide p99, aggregate something that **adds up**:
histogram bucket counts (Prometheus histograms, HDR histograms, t-digests),
or the raw samples if you can afford them. Then take the percentile once,
over the total.

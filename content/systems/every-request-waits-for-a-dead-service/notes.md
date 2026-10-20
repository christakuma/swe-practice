# A slow dependency is worse than a dead one

## Why an optional widget took the page down

A dependency that refuses connections fails in a millisecond. One whose hosts
have vanished fails only when the caller's timeout expires, here 5 seconds,
and for those 5 seconds the request holds a worker thread. Little's law gives
the demand: 40 requests a second × 5 seconds = **200 threads**, against a pool
of 64. The pool fills, requests queue for a thread, the queue grows, and the
service starts refusing requests that have nothing to do with recommendations.
The failure travelled up the call graph through a shared resource, the thread
pool.

## The three tools

**Timeouts from measurements.** Set a timeout just above the healthy tail
(here p99.9 = 240 ms, so about 250 ms), not at a round number. A timeout is
the most a failed call can cost you, and a timeout at p99 fails 1% of healthy
calls.

**A circuit breaker.** It counts failures, and past a threshold it *opens*:
calls fail immediately, with no network trip and no held thread. After a
cool-down it goes *half-open* and lets a few trial calls through; success
closes it, failure opens it again. Count only failures that say the
dependency is unhealthy (timeouts, refused connections, 503s), not correct
answers like 404 or the caller's own bugs like 400.

**A fallback.** The breaker decides *whether* to call; the fallback decides
what the page shows when it does not: an empty widget, a cached list,
"popular products". The page's contract is to render. Only the widget is
optional.

## Bulkheads, for next time

Even with all three, a slow dependency borrows threads from the shared pool
until the breaker opens. Giving each dependency its own small pool or
concurrency limit (a *bulkhead*) bounds how much of the service one
dependency can take with it. Michael Nygard's *Release It!* is the
standard reference for all four patterns.

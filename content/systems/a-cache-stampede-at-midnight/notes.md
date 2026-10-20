# A cache stampede, and why it keeps happening at the same time

## The synchronisation

A cache with a fixed TTL remembers when each key was loaded. Warm every key
in one pass and they all share an expiry; when they expire together, every
miss is reloaded in the same second, and they share an expiry again. A
one-off event, the warming three weeks ago, has become a nightly one that
nothing will undo. The database is idle at 23:59 and pinned at 00:00, and
nothing about the code is slow except that it all asks at once.

## Why each miss makes it worse

Cache-aside (`get`, and on a miss `load` then `set`) is fine one request at
a time. Under load, every request that misses before the first load
finishes starts a load of its own. At 100 requests a second per instance
and a load that takes 800 ms under saturation, that is about 80 identical
queries per product per instance: Little's law, with the load's latency
growing because of the very queries it is counting. It is a positive
feedback loop, and why the database pins rather than slows.

## Three fixes, and what each one does

- **Jitter the TTL.** `ttl = 24h - random(0, 1h)` spreads expiries over an
  hour, so misses arrive as a trickle. Cheap, and it removes the
  synchronisation, which is the root cause. A longer TTL does not: it makes
  the stampede rarer and exactly as large.
- **Coalesce the misses (single-flight).** Within one process, the first
  miss for a key starts the load and everyone else who misses while it runs
  awaits the same result. Loads in flight for a key drop from "request rate
  times latency" to one per process. Go's `golang.org/x/sync/singleflight`
  is the well-known version, and Varnish and nginx call it request
  collapsing. Two details make it correct: **share the failure** with the
  waiters rather than letting each retry, and **forget the flight once it
  lands**, success or failure, so a later miss loads the current value.
- **Serve stale while revalidating.** Keep the value past its soft TTL and
  serve it while one background refresh replaces it. No request waits for
  the database while a stale copy exists. It needs the business to accept
  a slightly old value, and here it does.

A **lock per key** looks like coalescing and differs in one way that
matters during an outage: when the load fails, each waiter takes the lock
in turn and tries again, so a dead database costs one full timeout per
caller, in series.

## Beyond one process

Single-flight bounds loads per instance; with twenty instances, twenty
loads of one key run at once. That is usually enough. If it is not, the
next step is a short lock in the cache itself (`SET key:loading NX PX
5000`) or probabilistic early expiration, where each read refreshes early
with a small, rising probability as expiry approaches (the "XFetch"
approach).

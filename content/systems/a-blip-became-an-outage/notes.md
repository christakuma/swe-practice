# Retries are load, and they multiply

## The arithmetic

Four layers, each making up to four attempts at the next, turn one tap into
up to **4⁴ = 256** database queries while the database is unreachable.
Retries at every layer multiply rather than add, which is the first thing
to check in any architecture where each service "handles failure" on its
own.

## Why it did not recover

When the network came back, the retries arrived together at about seven
times what the database could serve. Queries slowed, slow queries passed the
2-second timeouts, timeouts were retried, and the retries were the overload.
The system had settled into a stable broken state, a **metastable failure**,
that it could not leave without the load dropping. Disabling retries dropped
it, and the database recovered in thirty seconds.

## A retry policy that helps

- **Retry in one place.** Usually the layer closest to the failure, which
  knows what the error means. The layers above it pass failures up.
- **Retry only what is worth retrying.** Errors that say the work did not
  happen and may succeed later: connection refused, `503` (honour
  `Retry-After`). Not `400`s, which fail identically. Not timeouts on
  non-idempotent calls without an idempotency key, which may already have
  done the work.
- **Back off exponentially, with jitter.** Doubling waits spread the retries
  out. Random waits stop the clients that failed together from retrying
  together. "Full jitter" (`uniform(0, ceiling)`) is the variant AWS's
  architecture blog measured as finishing the work with the fewest calls.
- **Bound it.** A few attempts, then fail. A retry budget (retries ≤ 10% of
  requests, as in gRPC's retry throttling and Finagle) bounds the
  amplification even when every layer's policy is wrong.
- **Shed load and break circuits.** When a dependency is failing most
  calls, stop calling it for a while (see the circuit breaker incident in
  this track).

## The code

```python
def call_with_retries(operation, *, sleep, rng):
    for attempt in range(1, 4):
        try:
            return operation()
        except Unavailable:
            sleep(rng.uniform(0, 0.1 * 2**attempt))
    return operation()
```

The fourth attempt is outside the loop, so whatever it raises reaches the
caller unchanged, and nothing sleeps after it.

`sleep` and `rng` are passed in for the reason the tests show: a policy
whose timing is a function of its inputs can be tested exactly, with no
clock.

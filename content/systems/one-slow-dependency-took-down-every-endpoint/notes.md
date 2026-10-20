# Shared pools, Little's law, and bulkheads

## How a slow call becomes everyone's outage

A thread that waits on a network call is not idle from the pool's point of
view: it is taken. Little's law says how many are taken: **arrival rate
times time in the system**. Fifty tax calls a second at 50 ms occupy two
and a half threads, which nobody notices. At 30 s they occupy fifteen
hundred, and the pool has two hundred. It fills in four seconds, and from
then on every request, for every endpoint, waits in the accept queue for a
thread that a tax call is holding.

That is why `/catalog` and `/health` failed though they never call tax: the
resource they needed was shared with something that was stuck. And because
the health check failed too, the load balancer removed the instances,
turning "checkout is down" into "the site is down".

## Two controls, and what each one bounds

- **A timeout bounds how long one call holds a thread.** The right number
  comes from the budget, not from the library: 20 threads at 50 calls a
  second gives each call 0.4 s, comfortably above the healthy p99 of 180
  ms. The default of 30 s was never chosen by anyone who knew these numbers.
- **A bulkhead bounds how many threads one dependency may hold.** A
  separate pool, or a semaphore, sized for that dependency, and full means
  fail at once. It does not make checkout work while tax is down. It makes
  sure checkout is the only thing that does not.

They are complementary. The timeout limits the time per call and the
bulkhead limits the calls; either alone would have saved the catalog here,
and together they make the bound hold even when one of them is set wrong.

## What does not help

A **bigger pool** buys seconds: the demand is set by the dependency's
latency, which you do not control. **Retries** multiply the demand. A
**circuit breaker** is a good third layer and a poor first one: it trips on
calls that have finished, and with a 30-second timeout nothing finishes for
30 seconds.

## The health check

A health check that shares the request pool reports "the pool is busy" as
"the process is dead", and a load balancer acting on that removes capacity
in the middle of an overload. Serve liveness from something that does not
need a request thread, and keep readiness (should I get traffic?) separate
from liveness (should I be restarted?).

# A lock order decided by the data is not an order

## What happened

`transfer(source, target)` locked the source, then the target. That is an
order, but it is decided by *which way the money moves*. A sale from 42 to 17
locks 42 then 17, and the refund from 17 to 42 locks 17 then 42. When the two
run at the same moment, each takes its first lock and waits forever for the
second, which the other holds. Every later transfer touching 17 or 42 then
queues behind them, which is why the whole service froze rather than two
requests.

The promotion did not cause the bug. It made traffic between the same pairs,
in both directions, frequent enough for the window to be hit several times an
hour.

## The four conditions, and which one to attack

A deadlock needs **mutual exclusion**, **hold and wait**, **no preemption**
and **circular wait** at once. Mutual exclusion is the point of the lock. Hold
and wait can be removed (take both locks at once, or try-lock the second and
back off), but that usually means retry loops and, under contention, livelock.
**Circular wait is the cheap one to remove**: give the locks a global order
that does not depend on the request, and take them in it.

```python
def transfer(source, target, amount):
    if source is target:
        raise ValueError("cannot transfer to the same account")
    first, second = sorted((source, target), key=lambda account: account.id)
    with first.lock, second.lock:
        if source.balance < amount:
            raise InsufficientFunds(source.id)
        source.balance -= amount
        target.balance += amount
```

The balance check still uses `source` and `target`: only the *locking* is
reordered. The self-transfer check matters more after the fix than before.
With a plain `Lock`, sorting one account against itself and taking its lock
twice deadlocks a single thread.

## The fixes that are not

- **One lock for the whole ledger.** Correct, deadlock-free, and it turns
  sixteen workers into one. Fine for a prototype; not for a service whose
  throughput is the incident.
- **`acquire(timeout=...)` and carry on.** Ending the wait is good. Pretending
  the transfer happened is not. If you time out, raise, release everything,
  and let the caller retry. That is how databases handle it (see the Postgres
  incident in this track).
- **`RLock`.** Reentrancy is about one thread taking a lock it already holds.
  A deadlock is two threads.

## Finding the next one

The useful test does not try to make the deadlock happen. It records the
order locks are taken in and fails on a cycle, which shows up on the first
`transfer(a, b)` and `transfer(b, a)`, on one thread, every run. The Linux
kernel's **lockdep** works this way, and so does ThreadSanitizer's
*lock-order-inversion* report. A load test finds it only when the timing is
on your side.

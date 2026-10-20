# Check-then-act, and why the lock has to live where the data does

## The race

`reserve` reads the stock, decides, and writes. Each step is correct, and
the three together are not, because between the read and the write another
buyer can do all three. Both replicas read `stock=1`, both decide a pair is
left, and both write `stock=0`: one write lands on top of the other and a
sale vanishes. That is a **lost update**, and the general shape is
**check-then-act**: a decision made on a value that is no longer true by the
time it is acted on.

## Why the lock did nothing

A `threading.Lock` is a word in one process's memory. It serialises the
threads of `inventory-a` and has never heard of `inventory-b`. Mutual
exclusion has to be enforced by something every party goes through, and the
only thing both replicas share is the store. A Redis lock or a database
advisory lock would work for the same reason, and add a lease to get wrong
(see *the nightly job ran twice*).

## Three ways to close the window

- **Do it in one statement.** `UPDATE items SET stock = stock - $2 WHERE sku
  = $1 AND stock >= $2`, then look at the row count. The database takes the
  row lock, re-reads the current row and applies the condition to it, so the
  check and the write cannot be separated. Under contention this is the best
  of the three: buyers queue on the row lock and nobody's work is thrown
  away.
- **Lock the row while you decide.** `SELECT ... FOR UPDATE` in a
  transaction. Correct, and it holds the lock for as long as the application
  thinks, which matters when the thinking includes a network call.
- **Optimistic concurrency.** Read a version with the value, and write only
  if the version is unchanged (`put_if_version`, `UPDATE ... WHERE version =
  $v`, an `If-Match` ETag). No lock is held, and a lost write is retried
  from a fresh read. It is the only option when the store has no
  transactions, and it suits keys that are rarely contended. On one hot key
  it degrades: of everyone who read a version, one wins and the rest retry,
  so the store does most of its work failing.

What is *not* a fix: a transaction at READ COMMITTED around a plain SELECT
and an UPDATE. A transaction makes its writes atomic; it does not stop
someone else writing what you read.

## Two details in the fix

**Decide again after every lost write.** The write that beat yours may have
taken the last pair, so a retry that reuses the first read's decision sells
stock that is gone. **Bound the retries** and report contention, rather than
spinning: on a launch, an unbounded loop is a request that never answers.

## Catching it before launch day

Concurrency bugs like this need a test that forces the interleaving rather
than hoping for it. The hidden tests here play the other replica *inside*
the store's read, so the race happens on every run. A load test against two
real replicas, followed by a check that units sold never exceeds stock, is
the end-to-end version.

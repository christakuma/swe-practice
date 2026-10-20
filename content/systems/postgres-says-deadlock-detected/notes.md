# Row locks deadlock like mutexes, and the database breaks the tie

## The shape

An `UPDATE` takes a lock on every row it changes and keeps it until the
transaction ends. Two transactions that update the same two rows in opposite
orders are two threads taking two mutexes in opposite orders:

```
apply_payment:    lock account ........ wait for invoice
settle_invoice:   lock invoice ........ wait for account
```

The difference from an in-process deadlock is that Postgres notices. A
backend that has waited on a lock for `deadlock_timeout` (1 second by
default) checks the graph of who waits for whom. If it finds a cycle it
aborts **its own** transaction with SQLSTATE `40P01`, which releases that
transaction's locks and lets the other one finish. Which side loses depends
on whose check runs first, which is why the API failed some nights and the
job on others.

## Fixing it

Take rows in one order everywhere. The cheapest way is to order the
statements: `settle_invoice` updates the account first, like
`apply_payment`. When the natural order of the statements is the other way
round, lock the row you want first explicitly with `SELECT ... FOR UPDATE`.
Across many rows of one table, the same rule means sorting: update rows
`ORDER BY id`, or lock them with `SELECT ... ORDER BY id FOR UPDATE` first.

Things that do not fix it:

- **`deadlock_timeout`** decides when the check runs, not whether there is
  a deadlock. Raising it makes each deadlock hold its locks for longer.
- **Isolation levels.** Writes lock rows at every level. Postgres has no
  dirty reads at all: READ UNCOMMITTED behaves as READ COMMITTED.
- **Autocommit.** It works by giving up the atomicity the transaction was
  there for.

## And still retry

Ordering protects the paths you have ordered. The next path someone writes
may not be, so the client should treat `40P01` (and `40001`, a serialization
failure) as retryable: roll back, rerun the **whole** transaction from
`BEGIN`, a few times at most, with jittered backoff. Retrying only the failed
statement cannot work: once a statement fails, the transaction is aborted and
everything until `ROLLBACK` fails with `25P02`.

Watch the rate of `40P01` on a dashboard. One a night is a retry doing its
job, and a hundred is a design to fix.

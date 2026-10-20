# A lock with a timeout is a lease, and a lease can end without you

## What happened

`SET NX PX` is a correct, atomic way to take a lock that frees itself if
the holder dies. That last property is the point, and it is also the bug: a
lock that expires on its own can expire while its holder is alive and
merely **stopped**. A VM paused for host maintenance, a long garbage
collection, a process swapped out under memory pressure: in each, the
holder's clock and code are frozen, and the world's are not. billing-1 was
paused at 02:03, its lease ran out at 02:10, billing-2 was correctly given
the lock, and at 02:14 billing-1 resumed in the middle of its loop with no
idea any time had passed.

The general name for this is a **lease**: a lock granted for a period. It
is the right tool, because a lock that never expires is a lock a crashed
host holds for ever. But it means "I hold the lock" is a claim with a
timestamp on it, and the holder cannot know when its own claim lapsed.

## Why the holder cannot fix it alone

A longer TTL makes the pause that breaks it longer, and makes a crashed
holder block the job for longer. Renewing the lease runs in the paused
process too. Checking the lease before every write is check-then-act: the
check passes, the pause falls between the check and the write, and the
write lands. Anything the holder does, it does at one moment and relies on
at a later one.

## Fencing tokens

Have the lock service hand out a number that increases with every grant,
and make **the resource being written** remember the highest number it has
accepted and refuse anything lower. Now a holder whose lease lapsed is
stopped at the one point it cannot skip: its next write. That is Martin
Kleppmann's argument against using Redlock for correctness, and the reason
ZooKeeper and etcd expose a monotonic version (`zxid`, the revision) with
each lock. A Redis `SET NX` gives you no such number, so you have to issue
one yourself, for example with `INCR` alongside the `SET`.

The cost is that the storage must take part. A lock that only the clients
honour is advice.

## And make twice harmless anyway

Fencing decides who may write. Idempotency makes it not matter: a unique
constraint on `(customer_id, period)` means a second run's inserts do
nothing, whatever the locks say, and an idempotency key on the email
provider stops a second send of the same invoice. Checking for an invoice
before inserting is not the same thing; two overlapping runs both see none.

For a job like this, the lock is an efficiency measure (do not do the work
twice) and the constraint is the correctness measure (never bill twice).
Treat them that way round.

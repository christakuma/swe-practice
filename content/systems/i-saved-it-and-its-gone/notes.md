# Replica lag, and the reader who must not see it

## What happened

Writes go to the primary and reads to replicas, which apply the primary's
changes a little later: asynchronous streaming replication. "A little" is
40 ms usually, 800 ms sometimes, and seconds during a backup. The save
committed on the primary, the redirect came back 80 ms later, and the next
page read the profile from a replica that had not applied the change yet.
Nothing was lost. The user was shown the past.

## Who needs what

Most readers do not care whether a name changed 200 ms ago. The person who
changed it does, because to them the old name means "it did not save", and
they save again or call support. The guarantee they need has a name:
**read-your-writes**, a promise to the session that wrote, and to nobody
else. Making *every* reader see every write at once is a much stronger
property, and it would cost the replicas their reason to exist.

## Ways to give it

- **Route the writer to the primary for a while.** After a write, set a
  flag in the session (or a cookie) that sends that user's reads to the
  primary for longer than the worst lag. Simple, and the window has to
  cover the worst case, not the typical one.
- **Read from a replica only once it has the write.** Record the primary's
  WAL position after the write (`pg_current_wal_lsn()`), and before reading
  check a replica's `pg_last_wal_replay_lsn()`; use it if it is past that
  position, otherwise try another or the primary. Precise, and more moving
  parts. MySQL's GTIDs and MongoDB's causal consistency sessions are the
  same idea.

What does not work: sleeping before the redirect (it covers the median and
slows every save), more replicas (less lag, never none), and rendering the
submitted values on the confirmation page (fixes one page; the next one
reads from a replica).

## Time going backwards

Read-your-writes does not stop a different oddity: two replicas at two
different lags, and a user whose refreshes alternate between them, seeing
the new value, then the old, then the new. The guarantee that rules this out
is **monotonic reads**: never see an older state than one you have already
seen. Pin a session to one replica, or apply the same "at least this WAL
position" rule to every read the session makes, advancing it as the session
sees newer data.

These two, with monotonic writes and writes-follow-reads, are the
**session guarantees** from Terry et al.'s Bayou work: what a single user
can be promised by a system that, overall, is only eventually consistent.

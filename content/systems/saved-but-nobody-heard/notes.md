# The dual write, and the transactional outbox

## Two systems, no transaction across them

`place_order` writes the order to Postgres, then publishes a message to the
broker. Each write can succeed or fail on its own, and between them there
is a moment where the first has happened and the second has not. A broker
timeout, a crash, an OOM kill or a deploy landing in that moment leaves an
order that is paid for and that no other system will ever hear about. With
enough traffic, that moment is hit every day: 214 times in a month here.

This is the **dual-write problem**, and it has no fix in the order of the
two calls:

- **Database first** (the original): a failure in between loses the
  message.
- **Broker first, or inside the transaction**: a failure in between sends a
  message for an order that then rolls back, and the warehouse ships an
  order nobody placed. The broker cannot be rolled back.

Two-phase commit across both would solve it in principle, and almost no
broker offers it, for good reasons of cost and availability.

## The transactional outbox

Make it one write to one system. In the same transaction as the order,
insert a row into an `outbox` table holding the message. Either the order
and its message both exist or neither does. A separate **relay** reads
committed outbox rows, publishes them, and marks them sent. The relay can
fail, retry and restart as often as it likes, because the row stays there
until the broker has confirmed it.

## What the relay guarantees

**At least once.** A relay that crashes after publishing and before
marking the row will publish it again. So the outbox does not remove the
need for idempotency, it relies on it: the warehouse must recognise an
order it has already seen, by order id. (See *two welcome emails*.)

Ordering is the other detail. A single relay reading oldest first preserves
commit order per table; several relays in parallel do not, unless each
handles its own partition, say by order id.

## Change data capture

Debezium and similar tools read the database's write-ahead log and publish
committed changes. Pointed at the outbox table, they replace the polling
relay: no query loop, commit order for free, and still at least once,
because a restarted connector replays from its last saved position.
Pointing them at the order table itself skips the outbox, at the price of
making every consumer depend on that table's columns.

## The 500

The original code also told the customer their order failed when it had
been committed, which invites a second order. With an outbox, the request
returns after the commit and the message is the relay's problem; the
customer's answer no longer depends on the broker being up.

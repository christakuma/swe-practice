# At-least-once delivery, and the consumer that makes it safe

## Why the message came back

A queue learns that a message is done when the consumer acks it. If no ack
arrives within the visibility timeout, the broker cannot tell "finished and
forgot to say" from "died halfway", so it delivers the message again. That
is **at-least-once delivery**, the default of SQS, RabbitMQ with manual
acks, Kafka consumers, and almost everything else, because the alternative
loses messages.

The worker sent the email, then a deploy's SIGTERM arrived in the second
before the ack. A minute later, another worker got the message and sent the
email again. Nothing was broken. Every component did what it promises.

## The two wrong fixes

- **Ack first.** That is at-most-once: a crash after the ack and before the
  send loses the email for good. Duplicates become losses, which the
  business said is worse.
- **Exactly-once from the broker.** Kafka's exactly-once semantics are
  real, and they cover consuming from Kafka and producing to Kafka in one
  transaction. An email, an HTTP call or a payment is outside that
  transaction, and no broker can commit its own offset and an external side
  effect as one step. There is always a moment after the side effect and
  before the commit.

## The idempotent consumer

Accept that a message may arrive more than once, and make the second
arrival do nothing:

- **Use the side effect's own idempotency**, when it has one: send with a
  key and let the provider refuse a repeat. Here the email provider takes a
  key, so this is the whole fix.
- **Otherwise, record what you have done** in the same transaction as the
  work: insert the key into a `processed` table with a unique constraint,
  and skip the work if the insert conflicts.

## Choosing the key

The key should name **the thing that must happen once**, not the delivery
that carried it. A message id catches redeliveries and misses a producer
that published twice, since each publish gets a new id. `welcome:<user_id>`
is the same for every copy of the event, however it was duplicated. A
timestamp or a fresh UUID is different every time, which is no key at all.

## Graceful shutdown helps, and is not the fix

Handling SIGTERM by finishing the current message and acking it before
exiting would have avoided this particular duplicate on deploys. It would
not avoid the ones from crashes, OOM kills, network partitions or a
producer that published twice. Do it for the deploys, and build the
consumer as if it were not there.

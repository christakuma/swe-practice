# N+1: the queries are fast, and there are too many of them

## Reading the trace

Every product span takes about 16 ms, the round trip to a database in
another zone, and there is one span per line item. Nothing in that picture
is slow: no query is in the slow-query log, the database's CPU is idle, and
each lookup is by primary key. The page is slow because it **waits for 250
round trips one after another**. That is the N+1 pattern: one query returns
N rows, and the code then runs one more query per row. It hides well, because
every test order and every developer's sample data has three items.

## The fix is fewer trips, not faster ones

Ask for all the products at once: `WHERE id = ANY($1)`. Two details decide
whether that is correct:

- **Respect the batch limit.** A repository that takes 100 ids per call
  needs `ceil(distinct / 100)` calls, here three for 250 products. Real
  limits exist: bind-parameter caps (65,535 in Postgres's protocol), query
  size limits, and a planner that stops using the index well past a few
  thousand ids.
- **Ask for each product once.** Two lines naming the same product need one
  lookup, and duplicate ids spend the batch budget on nothing.

After the fix, the page costs 2 + ceil(distinct / 100) round trips, about
80 ms for the worst order there is.

## Why not concurrency, and why not a cache

Running the 250 lookups in parallel is bounded by the connection pool. With
10 connections it is 25 rounds of 16 ms, about 400 ms, and for that time the
page holds every connection the service has. Batching sends one query that
does the same work and holds one connection.

A cache would make the second render fast and leave the first one slow. It
would also show stale stock, because nothing tells a process-local cache
that stock changed. That is a second design problem (invalidation, TTLs)
that the ticket did not ask for.

## Catching the next one

Assert on **query counts**, not only on output. A test that renders a
50-item order against a counting fake and fails above five queries would
have caught this on the day it was written. In development, tools that warn
on repeated query shapes per request (Django's `nplusone` or
`django-debug-toolbar`, Rails' Bullet) catch it with no test at all.

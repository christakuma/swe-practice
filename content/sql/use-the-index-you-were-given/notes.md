# `EXPLAIN QUERY PLAN`, and why rows cannot tell you this

Both answers in this drill are correct. They return the same two numbers in the
same order, and no check in `rows.py` — or in any grader that compares result
sets — can distinguish them. That is the gap this exercise is about, and it is
the reason the drill engine reads SQLite's query plan at all.

**Read the plan.** `EXPLAIN QUERY PLAN` in front of any `SELECT` gives you a few
lines of plain text. Two words carry almost all the information:

- `SEARCH orders USING INDEX idx_orders_customer (customer_id=?)` — SQLite is
  jumping straight to the matching rows.
- `SCAN o` — SQLite is reading every row of that table and testing each one.

A `SCAN` is not automatically wrong. Scanning four rows is faster than
consulting an index, and SQLite knows that; on a tiny table it will pick the
scan on purpose. What a `SCAN` tells you is that the cost of this query grows
with the size of the table, and that is the sentence that matters — because the
table you are testing against has six rows and the one in production does not.

**Why the slow answer is slow, exactly.** Here are the two plans, which is the
whole lesson:

```
-- SELECT total FROM orders WHERE customer_id = 2
SEARCH orders USING INDEX idx_orders_customer (customer_id=?)

-- SELECT o.total FROM orders o JOIN customers c ON c.id = o.customer_id
--  WHERE c.name = 'bob'
SCAN o
SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
```

The interesting thing is which table gets scanned, and it is not the one most
people guess. `customers` is *searched*, efficiently, by its primary key. It is
`orders` that is read whole — and the index on `orders(customer_id)` is not used
at all.

The reason is that the index can only be used if something gives SQLite a
`customer_id` to look for, and nothing does: the only filter is on
`customers.name`, which has no index of its own. So the planner inverts the
problem. It walks every order, looks up that order's customer by rowid, and
checks whether the name is bob. Correct, and linear in the number of orders —
which is the table that grows.

That is the generalisable habit, and it is not really about indexes: **an index
can only help if your `WHERE` is written against the column it covers.** A query
that filters on a joined-in column is asking the planner to work backwards, and
whether it can depends on what other indexes exist. The fast answer never
touches `customers` at all, because the prompt told you bob is customer 2 — and
the query that needs one table beats the query that needs two.

**What a plan will not tell you.** It is a plan, not a measurement — it says what
SQLite intends to do, not how long it took. For that you need real data and a
clock. The plan is the cheap check you can run on six rows and still learn
something true about six million, which is exactly why it is worth a check in an
offline drill.

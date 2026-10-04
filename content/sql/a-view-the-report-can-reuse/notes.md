# Where a filter goes once an outer join is involved

The hard part of this drill is not the view. It is that `WHERE` and an outer
join interact in a way that undoes the join.

`filtered-in-the-where.sql` is the answer almost everybody writes first:

```sql
FROM customers c LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.status <> 'cancelled'
```

Follow the pipeline. The `LEFT JOIN` produces a row for dana with every `orders`
column set to `NULL`. Then `WHERE o.status <> 'cancelled'` is evaluated against
that row: `NULL <> 'cancelled'` is `NULL`, which is not true, so the row is
discarded. The outer join did its job and the `WHERE` threw the result away.

**A `WHERE` on the right-hand table of an outer join turns it back into an inner
join.** That is the sentence to keep. It is not a quirk of this data — it is what
the pipeline does, every time, and it is why the bug survives review: the query
reads as "all customers, excluding cancelled orders" and executes as "customers
who have at least one non-cancelled order".

There are two fixes. Put the condition in the `ON` clause, where it filters what
the join *matches* rather than what survives it. Or put it inside the aggregate,
which is what the reference does:

```sql
SUM(CASE WHEN o.status <> 'cancelled' THEN o.total END)
```

`CASE` with no `ELSE` yields `NULL`, and `SUM` ignores NULLs — so a cancelled
order contributes nothing, and a customer whose every order is cancelled still
gets a row. `COALESCE(..., 0)` then turns dana's `NULL` sum into the `0` the
prompt asked for, because `SUM` over no rows is `NULL`, not zero.

**Why a view and not a query.** A view is a stored query: no data, nothing to
refresh, nothing to get out of date. Its value is that the decision above —
*cancelled orders are not revenue, and customers with no orders still count* —
gets made once, in a place with a name, instead of three times in three reports
by three people who each had to think it through. Two of whom did not.

That is also why `the-view-exists` is a required check and not an advisory one.
A query returning the right rows has answered the question; it has not done the
job.

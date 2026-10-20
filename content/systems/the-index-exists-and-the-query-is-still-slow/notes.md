# An index answers one question, and it is not always the one you ask

## What an index is

A B-tree index is the column's values, sorted, each pointing at its row.
It can find a value, or a range of values in sort order, by descending the
tree. That is all. Whether a query can use it is a question about whether
the query's condition is **a value or a range of the indexed expression**.

`WHERE email = $1` is. `WHERE lower(email) = $1` is not: the tree is
sorted by `email`, and `Ana@Example.com` and `ana@example.com` sit in
different places in that order, so the lowered value tells it nowhere to
look. Postgres lowers all twelve million emails and compares each one. The
index exists, `\d users` shows it, and the plan never touches it.

## The fix is to index what you ask about

`CREATE UNIQUE INDEX ON users (lower(email))` stores `lower(email)` for
every row, so the query's condition is now a lookup. Unique on the lowered
value, it also enforces what the case-insensitive change implied and the
old index did not: two accounts may not differ only in case. Build it with
`CREATE UNIQUE INDEX CONCURRENTLY` on a live table, and check first that no
such duplicates already exist, because the build fails if they do.

The `citext` type, which compares case-insensitively, is the other common
answer; it moves the rule into the column's type rather than every query.

## The same mistake in other clothes

- **A function or cast around the column**: `upper(name)`, `date(created_at)`,
  `id::text = $1`. The cure is an expression index, or rewriting the
  condition as a range on the bare column (`created_at >= $day AND
  created_at < $day + 1`).
- **A leading wildcard**: `LIKE '%for'` has no starting point in sort order.
  A trigram index (`pg_trgm`, GIN) is built for substring search.
- **Prefix `LIKE` and collation**: under a non-C collation, a B-tree on
  `name` cannot serve `LIKE 'Oka%'`; one built with `text_pattern_ops` can.
- **Column order in a composite index**: `(customer_id, created_at)` is
  sorted by customer first, so it serves "customer 42's orders this week"
  and cannot narrow "everybody's orders this week". Order the columns by how
  the queries filter: equality columns first, the range column last.

## Measuring, carefully

`EXPLAIN` shows the plan and the planner's estimates. `EXPLAIN (ANALYZE,
BUFFERS)` runs the query and shows what actually happened, row counts and
pages read included, and the gap between estimated and actual rows is
usually where a slow plan comes from. Because it **runs** the statement,
wrap anything that writes in `BEGIN; ... ROLLBACK;`.

## Catching it next time

Run `EXPLAIN` on the queries a change touches, in review, against a
database with realistic row counts; a sequential scan of a 12-million-row
table on a login path is visible in one line. `pg_stat_statements` ranks
queries by total time in production, which is where this one would have
been top of the list the morning after.

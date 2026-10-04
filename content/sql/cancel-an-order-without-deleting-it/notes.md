# Grading the table, not the result

This is the first drill in the track where the answer returns nothing, and that
makes it the one that explains why the engine looks at the database at all.

An `UPDATE` reports no rows. Not "1 row changed" — nothing a `SELECT` could
show you. So every check in `rows.py` is blind to this drill, and a grader that
only compared result sets would pass `UPDATE orders SET status = 'cancelled'`
without a murmur. What tells a right answer from that one is the six rows the
table is holding afterwards.

That is the same shape of problem as the git track's central finding: a revert,
a `reset --hard` and a forgotten push all leave byte-identical files, so the
check that discriminates is the one about where a ref points, not the one about
content. Here the check that discriminates is `table_matches`.

**Why it compares the whole table.** Grading "order 4 is cancelled" would pass
`no-where.sql`, which cancels order 4 *and the other five*. The only way to
catch an over-reaching `UPDATE` is to assert what did **not** change, and the
cheapest way to assert that is to compare everything. For a table too wide to
write out, the equivalent is a row count plus a `SELECT` of the columns you care
about — but notice that is strictly weaker, and in a real migration the weaker
version is how people find out a week later.

**The habit worth building.** Write the `WHERE` first, as a `SELECT`, and look
at what comes back. `forgot-the-date.sql` is the counter-example for people who
skip that step: it is a reasonable-looking clause that matches two rows instead
of one, and the table still has six rows afterwards, so nothing except a
full comparison notices.

**Cancelled is not deleted.** The advisory check is the only one here that reads
your SQL, and it is advisory on purpose — if you reached the right end state, you
got it right. But the distinction it is pointing at is a real one: a cancelled
order is a thing that happened and then stopped; a deleted order is a thing the
database claims never happened. Soft deletion exists because the second
sentence is almost never true.

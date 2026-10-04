# Where the filter goes, and why `LIMIT` needs something to cut

**`WHERE` before `GROUP BY`.** This drill has one filter and one place it can
sensibly go: `WHERE o.status <> 'cancelled'` removes the order before it is ever
summed. The alternative that looks equivalent and is not is filtering
afterwards — `HAVING`, or a condition on the aggregate — which answers a
different question: *of the customers whose total includes no cancelled money,
who spent most?* With this data the two differ only in bob's number; with real
data they differ in which customers appear at all.

The order is worth memorising as a pipeline, because almost every SQL surprise
is a misunderstanding of it:

```
FROM / JOIN  ->  WHERE  ->  GROUP BY  ->  HAVING  ->  SELECT  ->  ORDER BY  ->  LIMIT
```

Two consequences fall straight out of it. You can `ORDER BY` an alias defined in
the `SELECT` list, because ordering happens after selection. You cannot `WHERE`
on one, because filtering happens before.

**Why two and not three.** Four customers, and only three have ever paid for
anything — dana has never ordered, and an inner join drops her. So a `LIMIT 3`
would cut nothing, pass, and tell you nothing about whether you had written it
at all. This drill asked for two so that the `LIMIT` has something to do.

That is not a quirk of a small exercise. A `LIMIT` that happens to exceed the
number of rows available is the most common way a "top N" query is wrong without
anybody noticing: it works in development, where the table is small, and starts
returning a hundred rows in production, where it is not. The habit is to check
how many groups your query produces *before* the `LIMIT`, which is exactly what
`forgot-the-limit.sql` would have revealed.

**Rounding is the solver's job, deliberately.** The grader compares `spent`
textually, so `77.5` matches and `77.49999999999999` does not. That is not the
engine being fussy — it is the exercise. `SUM` over floats accumulates
representation error, and the moment a number leaves your query it is somebody
else's input: a CSV, a dashboard, an invoice. A grader that quietly rounded to
match would be teaching you that the precision of your output is not your
problem, which is the opposite of true.

For money specifically, the real answer is usually not `REAL` at all — store
pence as an `INTEGER` and divide at the edge. `ROUND(..., 2)` is the fix
available when the column is already a float, which in a real codebase it
usually is.

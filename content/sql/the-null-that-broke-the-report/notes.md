# Label the awkward row; do not filter it

Two wrong answers, failing in opposite directions. One loses a customer
entirely. The other keeps her in the right group and counts her as nothing.

**Losing her.** `WHERE city IS NOT NULL` is the first thing most people reach
for, because it makes the strange-looking row go away. It also makes dana go
away: the report now says three customers where there are four, and nothing in
the output admits it. Nobody notices a total that is quietly too small — that is
the whole problem with it. If a row is awkward, label it.

**Counting her as nothing.** `COUNT(city)` instead of `COUNT(*)` groups
correctly and then reports `unknown, 0`:

```sql
SELECT COALESCE(city, 'unknown') AS city, COUNT(city) AS customers
```

`COUNT(x)` counts non-NULL values of `x`. The defining property of that group is
that `city` is NULL in it, so there is nothing to count, and the answer is a
group that exists with nobody in it. The total adds up to three again — by a
different route, and just as silently.

This is the same rule as `one-row-per-customer`, pointing the other way, which
is why the two drills are worth doing in order. **`COUNT(*)` counts rows;
`COUNT(x)` counts values.** There, the rows came from an outer join, so a
customer with no orders had a row full of NULLs and `COUNT(*)` wrongly counted
it — `COUNT(o.id)` was right. Here the rows are customers, every one of them
real, and `COUNT(*)` is right. Same function, opposite verdict, and the whole
difference is what a row *is* at that point in the pipeline. Ask that question
before reaching for either spelling.

**One thing this data cannot show you, so it is written down instead.** Grouping
by the raw column —

```sql
 GROUP BY city                       -- rather than GROUP BY COALESCE(city, 'unknown')
```

— returns exactly the same three rows here, and it is tempting to call it a bug
anyway. It is not, quite. SQLite groups all NULLs together, so the partition is
identical; the two spellings can only diverge if some customer's city is
literally the string `unknown`, at which point the raw version merges a real
city with the missing ones and the `COALESCE` version keeps them apart. That is
a real hazard and a thin one, and it is the argument for choosing your sentinel
to be something no real value could be — `unknown`, here, only because this is a
drill. In a schema you own, the honest sentinel is the NULL itself and the label
belongs in the presentation layer.

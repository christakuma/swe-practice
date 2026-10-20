# Offset pagination counts rows in a list that moves

## What OFFSET means

`LIMIT 20 OFFSET 20` means "rows 21 to 40 of this query's result, as it is
right now". Between page one and page two, the list changed: three posts
arrived at the top, so every row moved down three, and rows 21 to 23 are the
three the user just read. A deleted post does the opposite: everything
moves up one, and the post that should have opened page two is skipped
without a trace. The query is correct each time it runs. The pages do not
join up because they are numbered against two different lists.

## And it is slow where it is used most

An index finds values, not positions, so `OFFSET 100000` is implemented by
reading 100,000 rows and throwing them away. Each page costs more than the
last, which is why crawlers and "export everything" jobs grind to a halt on
offset APIs.

## Keyset (cursor) pagination

Instead of saying how many rows to skip, say **where the last page ended**,
and ask for rows after it in the sort order:

```sql
SELECT id, created_at, body FROM posts
WHERE (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 20
```

New posts at the top are before the cursor, so they do not push anything
into the next page; a deleted post is simply not there. With an index on
`(created_at, id)`, every page is one index descent and twenty entries,
however deep.

Three details decide whether it is correct:

- **The cursor must name exactly one row.** `created_at` alone does not when
  two posts share a timestamp: `created_at < t` skips the rest of the tie.
  Add a unique tie-breaker (the id) to both the cursor and the `ORDER BY`.
- **The comparison is strict.** `<=` hands back the last row again.
- **The sort is the cursor.** Paging by `id` because it is unique only works
  if ids are in the order you show; imported rows with new ids are not.

Where row-value comparison is not available, `created_at < :t OR
(created_at = :t AND id < :id)` says the same thing.

## What it costs

Keyset pagination cannot jump to page 37, because there is no cursor for a
place nobody has reached. That is the right trade for feeds, timelines and
exports, which is why they offer "load more" rather than page numbers. For
an API, make the cursor opaque (base64 of the pair, or a signed token) so
clients cannot depend on its shape and you can change it later.

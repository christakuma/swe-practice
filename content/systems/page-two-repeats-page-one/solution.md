# Page two repeats the end of page one: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

why-repeats: rows-shifted
deep-pages: reads-and-discards
why-the-id: ties-skipped
what-keyset-cannot-do: jump-to-page

## page-by-keyset

```python
def feed_page(conn, cursor, size):
    if cursor is None:
        rows = conn.execute(
            "SELECT id, created_at, body FROM posts"
            " ORDER BY created_at DESC, id DESC"
            " LIMIT ?",
            (size,),
        ).fetchall()
    else:
        # Strictly after the last post the reader saw, in the same order the
        # page is sorted by. The id breaks ties between posts with one
        # timestamp, so the cursor names exactly one place in the list.
        created_at, post_id = cursor
        rows = conn.execute(
            "SELECT id, created_at, body FROM posts"
            " WHERE (created_at, id) < (?, ?)"
            " ORDER BY created_at DESC, id DESC"
            " LIMIT ?",
            (created_at, post_id, size),
        ).fetchall()
    if len(rows) < size:
        return rows, None
    last_id, last_created_at, _ = rows[-1]
    return rows, (last_created_at, last_id)
```

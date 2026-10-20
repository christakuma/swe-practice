# Page two repeats the end of page one: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

why-repeats:
deep-pages:
why-the-id:
what-keyset-cannot-do:

## page-by-keyset

```python
def feed_page(conn, cursor, size):
    offset = cursor or 0
    rows = conn.execute(
        "SELECT id, created_at, body FROM posts"
        " ORDER BY created_at DESC, id DESC"
        " LIMIT ? OFFSET ?",
        (size, offset),
    ).fetchall()
    next_cursor = offset + size if len(rows) == size else None
    return rows, next_cursor
```

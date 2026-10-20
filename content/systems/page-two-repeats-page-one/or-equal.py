"""Counter-example: the right keyset, compared with `<=` instead of `<`."""


def feed_page(conn, cursor, size):
    if cursor is None:
        rows = conn.execute(
            "SELECT id, created_at, body FROM posts"
            " ORDER BY created_at DESC, id DESC LIMIT ?",
            (size,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, created_at, body FROM posts WHERE (created_at, id) <= (?, ?)"
            " ORDER BY created_at DESC, id DESC LIMIT ?",
            (*cursor, size),
        ).fetchall()
    if len(rows) < size:
        return rows, None
    return rows, (rows[-1][1], rows[-1][0])

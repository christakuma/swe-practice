"""Counter-example: a keyset cursor on the id, as if ids were in time order."""


def feed_page(conn, cursor, size):
    if cursor is None:
        rows = conn.execute(
            "SELECT id, created_at, body FROM posts ORDER BY id DESC LIMIT ?",
            (size,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, created_at, body FROM posts WHERE id < ?"
            " ORDER BY id DESC LIMIT ?",
            (cursor, size),
        ).fetchall()
    if len(rows) < size:
        return rows, None
    return rows, rows[-1][0]

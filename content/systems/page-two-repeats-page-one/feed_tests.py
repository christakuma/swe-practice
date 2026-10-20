"""The hidden tests for paging the activity feed by keyset.

**A real table, and one that moves between pages.** What is wrong with
`OFFSET` is not visible on a table that holds still: page two of a fixed list
is the same whichever way it is fetched. So these tests page an in-memory
SQLite table and insert and delete posts *between* pages, the way the feed's
users do, and the answer is judged on whether the posts it hands back join
up into the list as it was.

**The ids are not in time order**, on purpose: posts imported from the old
system were given new ids and kept their dates, so an answer that pages by
`id` alone gets the order wrong. And one test puts six posts with one
timestamp across a page boundary, because a cursor that holds only the time
cannot say where inside a tie it stopped.

The cursor is opaque here. Every test hands back exactly what the previous
page returned, so an answer may shape it however it likes.
"""

from __future__ import annotations

import sqlite3

from solution import feed_page

SIZE = 20


def feed(posts: list[tuple[int, str]]) -> sqlite3.Connection:
    """A `posts` table holding `(id, created_at)` pairs, each with a body."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE posts ("
        " id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, body TEXT NOT NULL)"
    )
    conn.execute("CREATE INDEX posts_newest_first ON posts (created_at, id)")
    add(conn, posts)
    return conn


def add(conn: sqlite3.Connection, posts: list[tuple[int, str]]) -> None:
    conn.executemany(
        "INSERT INTO posts VALUES (?, ?, ?)",
        [(post_id, at, f"post {post_id}") for post_id, at in posts],
    )


def at(minute: int) -> str:
    return f"2026-10-19 {minute // 60:02d}:{minute % 60:02d}:00"


def scattered(count: int) -> list[tuple[int, str]]:
    """`count` posts a minute apart, whose ids run in a different order."""
    return [((minute * 37) % 101 + 1, at(minute)) for minute in range(count)]


def newest_first(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute("SELECT id FROM posts ORDER BY created_at DESC, id DESC")
    return [post_id for (post_id,) in rows]


def ids(rows: list[tuple[int, str, str]]) -> list[int]:
    return [row[0] for row in rows]


def walk(conn: sqlite3.Connection) -> list[int]:
    seen: list[int] = []
    rows, cursor = feed_page(conn, None, SIZE)
    seen.extend(ids(rows))
    for _ in range(50):
        if cursor is None:
            return seen
        rows, cursor = feed_page(conn, cursor, SIZE)
        seen.extend(ids(rows))
    message = "still handing back a cursor after 50 pages"
    raise AssertionError(message)


def test_the_first_page_is_the_newest_posts() -> None:
    """With no cursor, the page is the 20 newest posts, newest first, with bodies."""
    conn = feed(scattered(30))
    rows, _ = feed_page(conn, None, SIZE)
    assert ids(rows) == newest_first(conn)[:SIZE]
    assert rows[0] == (rows[0][0], at(29), f"post {rows[0][0]}")


def test_walking_every_page_sees_every_post_once() -> None:
    """Following the cursors through 47 posts sees each once, in order."""
    conn = feed(scattered(47))
    assert walk(conn) == newest_first(conn)


def test_a_tie_across_a_page_boundary_is_neither_lost_nor_repeated() -> None:
    """Six posts with one timestamp, split by the page boundary, all appear once."""
    # Newest first: seventeen posts a minute apart, then the six that share
    # minute 5, then two older ones. Page one ends three posts into the tie.
    posts = [(minute, at(minute)) for minute in range(10, 27)]
    posts += [(100 + n, at(5)) for n in range(6)]
    posts += [(1, at(0)), (2, at(1))]
    conn = feed(posts)
    first, _ = feed_page(conn, None, SIZE)
    assert ids(first)[-3:] == [105, 104, 103]
    assert walk(conn) == newest_first(conn)


def test_new_posts_do_not_repeat_on_the_next_page() -> None:
    """Five posts arrive after page one: page two is still the 20 after page one."""
    conn = feed(scattered(60))
    expected = newest_first(conn)
    first, cursor = feed_page(conn, None, SIZE)
    add(conn, [(200 + n, at(100 + n)) for n in range(5)])
    second, _ = feed_page(conn, cursor, SIZE)
    assert ids(first) + ids(second) == expected[: 2 * SIZE]


def test_a_deleted_post_does_not_make_one_skip() -> None:
    """A post on page one is deleted: page two is still the 20 after page one."""
    conn = feed(scattered(60))
    expected = newest_first(conn)
    first, cursor = feed_page(conn, None, SIZE)
    conn.execute("DELETE FROM posts WHERE id = ?", (ids(first)[3],))
    second, _ = feed_page(conn, cursor, SIZE)
    assert ids(second) == expected[SIZE : 2 * SIZE]


def test_the_last_page_says_there_is_no_more() -> None:
    """A page shorter than the page size comes back with no cursor."""
    conn = feed(scattered(25))
    _, cursor = feed_page(conn, None, SIZE)
    assert cursor is not None
    second, cursor = feed_page(conn, cursor, SIZE)
    assert len(second) == 5
    assert cursor is None


def test_an_empty_feed_is_one_empty_page() -> None:
    """A feed with no posts is an empty page with no cursor."""
    conn = feed([])
    assert feed_page(conn, None, SIZE) == ([], None)

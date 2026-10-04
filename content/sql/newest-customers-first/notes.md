# ISO-8601, and why this drill is about storage rather than sorting

`ORDER BY signed_up DESC` is the whole answer, and it is only that short because
of a decision made in `seed.sql`: the dates are stored as `'2026-01-15'`.

SQLite has no date type. A date is text, a number, or nothing — and which of
those you pick decides whether sorting works. `'2026-01-15'` sorts correctly as
text, because ISO-8601 puts the most significant component first and pads every
field to a fixed width. `'15/01/2026'` does not: it sorts by day-of-month, so
the 1st of December comes before the 2nd of January, and the bug shows up as a
report that is *mostly* in the right order.

The same property is why the grader can check this with `result_ordered_by`,
which compares textually. For a column of bare integers it could not — `10`
sorts before `9` as text — which is written down in the assertion's own
docstring rather than hidden, because a drill ordering by an integer has to
assert the literal rows instead.

Two things worth taking from a drill this small:

- **Store dates so that the ordering you need is the ordering you get for
  free.** ISO-8601 text, or an integer epoch. Never a locale format.
- **`ASC` is the default, so `DESC` is a thing you have to remember.** "Newest
  first", "highest first", "worst first" — the interesting direction is almost
  always the one that is not the default, which is why this is the single most
  common one-character SQL bug.

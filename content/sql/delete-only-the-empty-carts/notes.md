# `NULL` is not a value, and three of these answers prove it

The whole drill is one rule: **`NULL` means unknown, so any comparison with it
is unknown, and `WHERE` only keeps rows where the condition is true.**

Work through what each wrong answer did.

`DELETE FROM carts WHERE items = NULL` matches nothing. Not even row 4, whose
`items` *is* NULL. `NULL = NULL` evaluates to `NULL` — not true, not false —
and `WHERE` discards anything that is not true. This is why SQL has `IS NULL` as
a separate operator: it is the only way to ask the question, because the obvious
spelling is unanswerable by construction.

`DELETE FROM carts WHERE items = 0 OR items IS NULL` matches two rows, and it is
the interesting mistake. Whoever wrote it knew the rule above — that is where the
`IS NULL` came from — and then used it to paper over the gap rather than asking
what the gap meant. "We never counted" and "we counted none" are different facts
about the world, and only one of them is a cart you can throw away.

`DELETE FROM carts` matches everything, which is the mistake that does not need
explaining and does need the drill.

And the right answer, `WHERE items = 0`, is shorter than two of the wrong ones.
Row 4 is excluded automatically: `NULL = 0` is `NULL`, which is not true, so the
row is not matched. The rule that makes `= NULL` useless is the same rule that
makes the plain comparison correct here — you do not have to handle NULL, you
have to understand that it has already been handled.

**Three-valued logic, as one table.** Worth keeping:

| expression | result |
|---|---|
| `NULL = 0` | `NULL` |
| `NULL = NULL` | `NULL` |
| `NULL <> 0` | `NULL` |
| `NULL IS NULL` | `true` |
| `NOT NULL` | `NULL` |

The consequence people get caught by most often is the third row: `WHERE status
<> 'cancelled'` silently drops rows where `status` is NULL. In
`the-three-biggest-spenders` that filter is safe only because `status` is
`NOT NULL` in the schema — which is a thing you can only know by reading
`seed.sql`, and the reason it is in your workspace.

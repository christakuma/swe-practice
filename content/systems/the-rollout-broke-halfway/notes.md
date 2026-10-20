# Expand, migrate, contract

## Why the rename broke

A rolling deploy runs the old and new versions side by side for its whole
length, against **one** database. So every schema change has to work for two
versions at once, and for a rollback to the previous one. A rename cannot:
the old code reads `name`, the new code reads `full_name`, and only one of
them exists at a time. The failure rate fell as the deploy went on only
because there were fewer old instances left to fail.

## The sequence

Each step is a migration or a deploy, and each one works with the version
before it:

1. **Expand:** add a nullable `full_name`. Nothing reads it yet.
2. Deploy code that **writes both** columns and still reads `name`.
3. **Backfill** existing rows, in small batches. It comes after dual writes,
   so no row written in between is missed.
4. Deploy code that **reads `full_name`**, still writing both, so a
   rollback to step 2's version still finds `name` current.
5. Deploy code that **stops writing `name`**.
6. **Contract:** drop `name`.

It takes several deploys instead of one. That is the price of never having a
moment where some running code is wrong about the schema.

## Doing the database steps safely

- **Batches.** A single `UPDATE` over 40 million rows holds every row lock
  until it commits and writes 40 million row versions at once. Batches of a
  few thousand rows, each committed, with a pause, keep locks short and let
  replicas and vacuum keep up.
- **`lock_timeout`.** Even a metadata-only `ALTER TABLE` takes `ACCESS
  EXCLUSIVE` for an instant. If a long query holds a conflicting lock, the
  ALTER waits, and everything that arrives after it waits behind it. Set
  `lock_timeout` (a few seconds) and retry, so a migration can fail quickly
  instead of stalling the table.
- **Know what rewrites.** In Postgres 11+, adding a column with no default
  or a constant default is metadata-only. A volatile default
  (`DEFAULT gen_random_uuid()`), changing a column's type, or `SET NOT NULL`
  on a large table either rewrites or scans it. Strong Migrations (Ruby) and
  squawk (SQL) lint for these.

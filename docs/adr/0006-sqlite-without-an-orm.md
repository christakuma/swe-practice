# 0006 — SQLite with hand-written SQL and explicit mappers, not an ORM

- **Status:** accepted
- **Date:** 2026-10-02
- **Phase:** 6

## Context

Two aggregates need to outlive the process that created them. `Attempt` is the
session aggregate — a status, a copied-in policy, an event log of commands,
hints and saved solutions, and a `Verdict` once it is graded. `ReviewCard` is a
flat row of scheduling state. There is no third, and §13's non-goals rule out
the kinds of thing that would add one.

Four constraints come from decisions already made, not from preference.

**The store is reached only through a port.** `AttemptRepository` and
`ReviewRepository` were declared in Phase 1 with every other protocol
([ADR 0002](0002-ports-and-adapters-with-an-enforced-boundary.md)), and an
in-memory implementation of the first has existed since Phase 4 and is what every
application test uses. Whatever persistence is chosen has to fit behind an
interface that was designed without it, and leave the in-memory one still
correct — §13 requires two implementations of every port, and these two keep each
other honest.

**The domain is already written, and it does not want to be a schema.**
`Attempt` is the only mutable object in the system; it has `__slots__`, private
state, no public setters and no default constructor that could produce a
half-built one. `ExerciseId`, `AttemptId` and `Sha` validate in `__post_init__`
and cannot hold an invalid value. `Verdict.outcome` is derived and never stored.
None of that is incidental — each property has tests — and a persistence layer
that required any of it to change would be reversing an earlier decision rather
than implementing this one.

**It is a single-user local tool.** One person, on one machine, with a few
thousand attempts after years of use. The largest query anyone will ever run
returns a few dozen rows. There is no concurrency beyond a second `practice`
invocation in another terminal, and no deployment.

**The database is not disposable.** Workspaces live in the user cache and are
rebuildable from a fixture; an attempt history is not rebuildable from anything.
That affects where the file goes and how a schema change has to behave, and it
is the reason migrations are a question at all rather than "drop and recreate".

PLAN.md §2 reserved this decision and §12 reserved the number. This is it.

## Decision

**Storage is SQLite through the standard library's `sqlite3`, with SQL written
by hand and mappers written by hand in both directions. No ORM, no query
builder, no migration framework.**

Concretely:

- **One `Database`** holding a path, which **connects on first use**. Building
  the object graph must create nothing: `practice validate` builds every adapter
  and never reads a row, and a database appearing in the user's data directory
  because someone validated the content library would be a side effect with no
  visible cause. `test_building_the_graph_writes_nothing_to_disk` is that claim.
- **One connection per operation, inside one explicit transaction.** `sqlite3`
  connections are bound to the thread that created them unless that check is
  disabled, and a held connection makes "what is committed" depend on where the
  last `commit()` was. A connection per operation is thread-safe by
  construction, which Phase 7's web app needs, and commits at a boundary you can
  point at.
- **Transactions are SQL, not driver state.** The connection is opened with
  `autocommit=True` — in Python 3.12+ that means the driver does no implicit
  transaction management — and the context manager issues `BEGIN IMMEDIATE` and
  `COMMIT` itself. Forced by behaviour, not taste: `PRAGMA journal_mode=WAL`
  cannot execute inside a transaction, so `autocommit=False`, which opens one
  before the first statement, makes the WAL pragma fail on a fresh database.
- **Pragmas on every connection:** `journal_mode=WAL`, `foreign_keys=ON`,
  `synchronous=NORMAL`. The second is the load-bearing one. It is
  per-connection and off by default, so the `ON DELETE CASCADE` that stops an
  event log outliving its attempt is enforced by the connection rather than by
  the schema.
- **Numbered SQL files** in `adapters/persistence/sqlite/migrations/`, applied
  once each inside one transaction apiece, with applied versions recorded in a
  `schema_migrations` table. The runner refuses a gap, a duplicate number, and a
  database carrying a version this build does not ship.
- **Explicit mappers, as pure functions over `Mapping`s.** `attempt_row`,
  `event_rows`, `to_attempt`, `card_row`, `to_card`. They never see a
  connection, which is what lets them be unit-tested in milliseconds against a
  plain dict.
- **`Attempt.restore`**, a reconstitution classmethod on the aggregate, is the
  one domain change this decision required. See below.
- **Columns for what is queried, JSON for what is not.** Status, timestamps,
  ids and the policy's limits are columns. The hint list, the allowlist, one
  event's payload and a whole verdict are JSON in TEXT columns, because nothing
  ever queries inside them — they are loaded whole with their attempt.
- **Every table `STRICT`, with CHECK constraints** restating the aggregate's own
  invariants: the status/`finished_at`/`verdict` pairings, the `ease` floor, the
  non-negative counters.

### Reconstitution is not replay, and this is the part worth arguing about

The aggregate cannot be rebuilt through its own public API. The elegant-looking
alternative — construct, call `record_command` for each stored command, then
`complete` — is wrong in two ways.

It re-checks the **current** policy against a **past** attempt. An exercise
edited down from twenty-five commands to ten would make last month's attempts
unloadable, and the only way out would be to stop storing the policy — which is
the thing that makes the aggregate able to enforce anything at all (PLAN.md
§4.3). And it re-runs invariants that were satisfied when the events happened,
so the aggregate could refuse to load a row it had itself produced.

So `restore` bypasses the behavioural guards and enforces only what a *row* can
be wrong about: naive or out-of-order timestamps, and the three pairings between
status, finish time and verdict. The schema's CHECK constraints are the same
rules one layer down, which is deliberate duplication with different jobs — the
aggregate refuses to *reach* an impossible state, the schema refuses to *store*
one, and `restore` refuses to *load* one.

## Consequences

**What this buys.**

- **Zero dependencies for persistence.** `sqlite3` ships with Python. Nothing to
  install, nothing to pin, nothing to pull over a network the tool does not have.
- **The schema is a readable artifact.** `0001_initial.sql` is the schema, with
  the reasoning in comments beside the constraints. Nobody has to read Python to
  find out what is stored or infer a column from a class attribute.
- **The translation is unit-testable.** Because a mapper takes a `Mapping` and
  returns a domain object, the part of persistence that is easiest to get quietly
  wrong is tested without a database, and the round-trip test asserts the whole
  aggregate rather than one field at a time — a mapper's failure mode is silence,
  and a field nobody reads back persists as `None` for a year.
- **The domain stayed as it was.** No base class, no declarative fields, no
  identity map, no lazy loading, no `__init__` an ORM needed to be able to call.
  `Attempt` gained one classmethod and lost nothing.
- **Phase 6's swap was one line per repository**, which is the only evidence that
  the ports of Phases 1–5 were real. No use case, grader or CLI command changed.

**What it costs, and these are real.**

- **Every column is named four times** — in the migration, in the INSERT, in
  `attempt_row`, in `to_attempt`. A schema change touches all four, and the only
  thing that catches a missed one is a test. An ORM would make three of the four
  derived.
- **No schema-diffing tool.** A migration is a file somebody writes. Nothing
  compares the classes to the tables and tells you they have drifted; the
  round-trip tests do it indirectly, and only for the paths they cover.
- **The mappers are about 300 lines, most of it reading a row carefully.** Every
  `_text`/`_integer`/`_timestamp` helper exists so a malformed column names
  itself instead of surfacing as a `TypeError` inside a value object two frames
  down. It is dull code and there is more of it than the interesting code.
- **`BEGIN IMMEDIATE` on reads serialises them.** Correct and slightly wasteful:
  two readers queue on the write lock. Invisible for a single-user tool whose
  longest query returns a few dozen rows, and the thing to revisit first if that
  stops being true.
- **A rewritten event log on every save.** Saving an attempt deletes its event
  rows and reinserts them, which is O(n) per command and O(n²) over an attempt.
  At a 25-command budget that is nothing. At ten thousand events it would not be.
- **No migration down.** A database carrying a version this build does not ship
  is refused rather than downgraded, because the alternative is reading rows
  through a mapper that does not match them. Rolling back means restoring a copy
  of the file.

## Alternatives considered

**SQLAlchemy, with the ORM.** The closest to winning, and rejected on what it
would do to the domain rather than on weight. Mapping `Attempt` means either
declarative classes — which puts persistence concerns in the pure layer the
architecture test exists to keep clean — or imperative mapping, which needs the
aggregate to have a shape it can construct and populate: no `__slots__` with
private state, a default constructor, settable attributes. Every one of those is
a property the aggregate has tests for. The second cost is that an ORM's value
is *relationship management* — identity maps, lazy loading, cascades, dirty
tracking — and with two aggregates, one child collection and no shared
references, there is nothing for any of it to manage. It would be the clearest
instance of the risk §13 names: an abstraction added because it looks
professional. It is the right answer the moment there are a dozen tables with
foreign keys between them.

**SQLAlchemy Core only, no ORM.** Genuinely attractive: typed table objects,
composable queries, a real migration story through Alembic, and no mapping
imposed on the domain. Rejected because the queries here are seven statements,
none of them composed or conditional, and a query builder's value is in the
queries you cannot write as a literal. It would also drag in Alembic, whose
value is multi-developer migration branching — a problem one person on one
machine does not have. If a Phase 11 progress page needs dynamic filtering over
several tables, this is what it becomes.

**A document store: JSON files on disk, one per attempt.** Very nearly enough,
and the thing to beat for a while. An attempt is loaded whole and written whole,
which is exactly what a file does, and it would delete the entire mapper layer.
Rejected on the two queries that are not about one attempt: `active()` and
`due_on(day)` would each become "read and parse every file", and the first runs
on every `gc` and every resume prompt. The second reason matters more —
atomicity. Saving an attempt is one row plus its events, and a file-per-attempt
store has no transaction, so a process killed mid-write leaves a truncated
attempt rather than no change. `BEGIN IMMEDIATE`/`COMMIT` is the whole answer and
it is free.

**TinyDB, or any embedded document database.** Adds a dependency to get less
than SQLite already ships: no transactions worth the name, no constraints, no
indexes, and a query language to learn. The only argument for it is avoiding SQL,
and SQL is the thing this project should be able to show someone.

**Event sourcing the attempt properly** — the log as the only truth, state
rebuilt by replay. Architecturally tempting, because the aggregate already keeps
a full event log and the advisory checks already read it. Rejected for the reason
in the decision above: replay through the public API re-applies *today's* policy
to *last month's* events, and an attempt has to be judged under the rules it was
started under. Making replay work would mean versioning the policy alongside the
events, which is storing the state anyway with extra steps.

**`pickle`, or `dataclasses.asdict` straight to a blob.** Quick, and it couples
the stored bytes to the Python class layout: renaming a field or moving a module
breaks every stored attempt, with no migration path and no readable file to
repair. Also unqueryable.

**No persistence at all; keep the in-memory store and accept the limitation.**
Worth stating because it was the status quo for five phases and cost nothing.
Rejected because it caps the product: `practice gc` cannot define an orphan
without an attempt table, the resume-or-abandon promise of §8.1 cannot be kept,
the web workbench of Phase 8 needs an attempt to survive an HTTP request, and
spaced repetition in Phase 9 is meaningless if nothing is remembered between
runs. Four later phases are blocked on this one.

## Revisit if

- A query arrives that is genuinely dynamic — a progress page filtering by tag,
  difficulty, outcome and date range at once. Hand-written SQL stops being the
  simple option around the third optional `WHERE` clause, and SQLAlchemy Core is
  the next step, not the full ORM.
- A third and fourth aggregate appear with real relationships between them, at
  which point identity mapping and cascades start managing something.
- The tool stops being single-user — a shared library, a classroom deployment —
  which changes the concurrency story, the connection story and probably the
  database.
- An attempt's event log grows past the low thousands, which would make the
  delete-and-reinsert save strategy the obvious thing to fix first.
- Migrations need to be reversible, or two people need to add one at the same
  time. Then Alembic is solving a problem that exists, rather than one it brought.

# Architecture decision records

One file per decision, numbered, append-only. Written when the decision is
made — not reconstructed afterwards, because a retrofitted ADR records the
justification and loses the alternatives, which is the half worth keeping.

## Process

1. Copy [`template.md`](template.md) to `NNNN-short-title.md`, next number up.
   Numbers are never reused, and a file is never deleted.
2. Open it as `proposed` if it is still being argued, `accepted` if it is not.
3. A decision that is reversed gets a **new** ADR. The old one is marked
   `superseded by ADR-NNNN` and its text is left exactly as it was — the point
   of the record is what was believed at the time.
4. Add it to the index below and to the table in [PLAN.md §12](../PLAN.md).

Scope: decisions that are expensive to reverse or that a reader would otherwise
have to reverse-engineer from the code. Library choices that could be swapped in
an afternoon do not need one.

## Index

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | accepted |
| [0002](0002-ports-and-adapters-with-an-enforced-boundary.md) | Ports and adapters, with the boundary enforced by a test | accepted |
| [0003](0003-grade-git-exercises-by-repo-state.md) | Grade git exercises by repo state, not command text | accepted |
| [0004](0004-content-as-declarative-data.md) | Content is declarative data, validated by schema | accepted |
| [0005](0005-sandbox-via-temp-dirs-and-subprocess.md) | Sandbox via a scoped directory and subprocess, not containers | accepted |
| [0006](0006-sqlite-without-an-orm.md) | SQLite with hand-written SQL and explicit mappers, not an ORM | accepted |
| [0007](0007-htmx-over-a-single-page-app.md) | HTMX and server-rendered fragments, not a single-page app | accepted |
| [0008](0008-sm2-first-with-fsrs-behind-a-port.md) | SM-2 first, with FSRS behind the same port | accepted |
| [0009](0009-ship-our-own-prompts.md) | Ship our own prompts; never redistribute problem text | accepted |
| [0010](0010-codemirror-5-over-6.md) | CodeMirror 5 over 6, to avoid an npm build step | accepted |
| [0011](0011-reference-solutions-are-command-lists.md) | Reference solutions are command lists, not shell scripts | accepted |
| [0012](0012-inspect-the-repository-through-the-grading-port.md) | The repo state panel reads through the grading port, not a second git path | accepted |
| [0013](0013-grade-on-save-is-a-preview.md) | Grade-on-save is a preview that persists nothing | accepted |
| [0014](0014-a-hand-ordered-curriculum-manifest.md) | A hand-ordered curriculum manifest, not a prerequisite graph | accepted |
| [0015](0015-verify-on-the-working-tree-not-every-commit.md) | Verify on the working tree, not on every commit | accepted |
| [0016](0016-a-generated-demo-not-a-recorded-one.md) | The demo is generated from captured output, not recorded | accepted |
| [0017](0017-a-front-door-separate-from-the-server.md) | A front door (`practice up`) separate from the server | accepted |
| [0018](0018-fsrs-as-a-second-scheduler-not-a-replacement.md) | FSRS as a second scheduler, not a replacement | accepted |
| [0019](0019-sql-drills-as-a-third-exercise-kind.md) | SQL drills as a third exercise kind | accepted |
| [0020](0020-interview-mode-withdraws-affordances-it-cannot-contain.md) | Interview mode withdraws affordances it cannot contain | accepted |
| [0021](0021-content-packs-install-rather-than-mount.md) | A content pack is installed to a directory, not mounted as a library | accepted |
| [0022](0022-counter-examples-are-run-against-the-bug-they-name.md) | Counter-examples are run against the bug they name | accepted |

0022 is the odd one in this set: the only record here about **how the content is
authored** rather than how the code is arranged. It exists because Phase 17's
adversarial tests -- the ones whose docstrings say "a solution that clamps the
tally at zero returns ..." -- were claims about code nobody had written, and
nine of them were wrong. The cheapest to describe was a counter-example meant to
separate real backtracking from a permanent visited set: a 3x3 ring of letters
that reads as obviously discriminating, and that the broken solution passes.

What makes it an ADR rather than a note is that the existing guard genuinely
cannot catch this. `tests/content/test_katas.py` proves the reference passes and
the stub fails, and is careful in its own docstring to claim no more; every one
of the nine defects left the reference passing. So the decision is a procedure
with a cost -- an oracle per kata, usually the solution the prompt bans -- and
0022's longest alternative is the declared `counter_examples` that git scenarios
already have in their schema (§5.4), rejected because the useful
counter-examples here are oracles over a swept input space rather than single
inputs. A 2x2 grid is the minimal case only because 380,000 grids were tried,
and a declared counter-example records the answer without the search.

0015 is the one record here that was not written on the day the decision was
made — it was decided in Phase 11 and written up in Phase 12. Its own first
section says so and says why it is an exception rather than a precedent: the
reasoning and the measurements were recorded contemporaneously in PLAN.md, so
what the ADR adds is the alternatives section, not a reconstruction.

0009, 0010 and 0011 are out of sequence because their numbers were reserved in
PLAN.md §12 before the decisions were written up, and numbers are never reused.
0009 waited longest: it is about what `content/` ships, so it could not honestly
be written until Phase 11 had shipped fifty-one exercises and found out what
writing them cost.

Every number reserved in PLAN.md §12 is now written.

0018 is the first record written after v1.0.0, and the first that exists to
report on an *earlier* one: ADR 0008 made two checkable predictions about the day
FSRS arrived, and 0018 says which of them held. That is the shape worth repeating
— a decision deferred with a stated prediction is a decision that can later be
graded, and the grade belongs in the record rather than in a commit message.

0019 is the second of that shape and the more interesting grade, because the
prediction it reports on was only half right. `domain/exercise.py` claimed a
third exercise kind would cost "a spec and a registry entry"; the spec and the
entry were exactly as cheap as promised, and what the claim missed is that two
kinds is the number at which *is this a kata* and *does this have a file to
edit* are indistinguishable. Five call sites had been asking the first and
meaning the second. An ADR that said the prediction held would have been a
worse record than one that says where it did not.

0020 is the third, and the first to report a prediction that could not be met
rather than one that was only partly met. PLAN.md's menu said interview mode
touches *application-layer policy*; two of its three clauses do, and the third
-- *no test peeking* -- turned out to be asking for containment, which PLAN.md
§8.1 had already ruled out in Phase 3 on the grounds that the solver owns the
machine. So 0020 records a feature that ships *less* than its own menu entry
promised, names the weaker thing it ships instead, and spends its longest
alternative on the stronger version it rejected and what would justify building
it. A record that quietly redefined "no test peeking" to mean what was built
would have been the easier document and a useless one.

0021 is the fourth of that shape, and the first where the menu's **Touches**
column was wrong in the *useful* direction. It said a content pack costs "a
content repository adapter"; the adapter was exactly that cheap, and what the
claim missed is that `ContentRepository` is not the only way to the library.
`SandboxProvisioner` is handed a content *root* and reaches exercise files by
path, because `pytest`, `bash` and SQLite all need a real file on a real disk.
So a pack-backed library can be browsed and not solved, and 0021's longest
alternative is the widened port that would have fixed that -- rejected because
the files have to be written to a directory either way, so widening the port
moves the extraction into `provision` and makes it happen per attempt rather
than once. Two readers of one library, named on the port so the next person does
not have to rediscover it.

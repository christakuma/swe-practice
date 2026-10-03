# 0009 — Ship our own prompts; never redistribute problem text

- **Status:** accepted
- **Date:** 2026-10-03
- **Phase:** 11 (content build-out) — number reserved in PLAN.md §12 since Phase 0

## Context

Phase 11 writes fifty-one exercises. Thirty of them are katas, and most are
recognisable: two sum, coin change, edit distance, longest increasing
subsequence. These are **standard problems** — they appear in Cormen, in
Skiena, in every interview-preparation site, and in LeetCode, HackerRank and
Codewars.

Three distinct things are easy to conflate, and the decision depends on keeping
them apart:

1. **The problem.** "Find two positions in a list whose values sum to a target."
   An idea. Not copyrightable, and in most of these cases decades older than any
   site that hosts it.
2. **The problem statement.** The specific prose a site wrote: its examples, its
   constraints section, its phrasing, its variable names. A creative work, owned
   by whoever wrote it, and in LeetCode's case explicitly covered by terms of use
   that prohibit reproduction.
3. **The test cases.** A site's hidden test suite is its product. Scraping it is
   both a licence violation and, for this project, pointless — the suite has to
   run offline against a stub we define.

The tempting shortcut is real and worth naming: a Phase 11 that copied thirty
problem statements and thirty test suites would be a weekend rather than a
fortnight. It is also the thing that makes the repository unpublishable, which
is a strange outcome for a portfolio project.

The project's own content rules push the same way for a non-legal reason. The
notes are "where the *why* lives and the why is the entire product" (PLAN.md §9),
and a kata's hidden suite is required to be *discriminating* — to reject a
plausible wrong answer and not merely an empty stub. Neither of those can be
copied, because neither exists on the sites the text would come from.

## Decision

**Every prompt, hint, note, test suite and reference solution in `content/` is
written for this repository.** Specifically:

- **Prompts are written from the problem, not from anyone's statement of it.**
  Where a standard problem is used, the function name, the signature, the
  examples and the constraints are ours. Several are deliberately renamed so
  that the source is irrelevant as well as unused: `longest_unique_run` rather
  than "longest substring without repeating characters", `best_haul` rather than
  "house robber", `rooms_needed` rather than "meeting rooms II",
  `fewest_coins`, `can_segment`, `max_slice_sum`.

  **Directory names are the deliberate exception.** `content/katas/house-robber`
  keeps the name the problem is known by, because the id is how a solver finds
  it and how `practice solve` is typed, and making the library unsearchable
  would be a cost with no benefit — a slug is not a creative work. The prompt,
  the title, the signature and the tests inside it are all ours.
- **Test suites are written from the specification**, one test per behaviour the
  prompt promises, plus at least one per kata aimed at a specific plausible wrong
  answer. Every expected value is computed against our own reference
  implementation before it ships.
- **Notes are original explanation**, and are the part of each exercise with the
  most work in it. Where they name a published result they name it — Floyd's
  cycle detection, Kahn's algorithm, Kadane, Levenshtein — because attribution of
  an *idea* is the opposite of the problem this ADR is about.
- **Git scenarios have no upstream to copy from at all.** No site poses "undo a
  commit that is already on origin" as a gradable exercise, which is the gap
  PLAN.md §1 is written against. Their fixtures, prompts and checks are original
  by necessity.
- **No scraping, no vendored problem sets, no "adapted from" text.** A content
  pack that imported someone's problems would be a Phase 13 idea and is not one.

## Consequences

**What it buys.**

- The repository can be public, cloned, forked and shown to an interviewer
  without a licence question anywhere in it.
- Prompts can state exactly what the grader checks. A copied statement would
  describe a *different* suite's expectations, and the mismatch would surface as
  exercises that are unsolvable as written — the failure mode the content suite
  exists to catch, imported deliberately.
- Writing the prompt is what finds the discriminating test. `validate-a-binary-
  search-tree` ships a tree that a per-node check accepts; `flood-fill` ships the
  no-op fill that loops forever. Neither came from reading a problem statement;
  both came from writing one and asking what a wrong answer would look like.
- The notes become the product rather than a restatement, because there is
  nothing to restate.

**What it costs.**

- Phase 11 took a fortnight of authoring rather than a weekend. Fifty-four
  exercises, each with five files, and the prose is the bulk of it.
- Renaming standard problems makes them slightly harder to look up when a solver
  is stuck. Mitigated by the notes, which name the technique and the published
  result plainly.
- Our test suites are smaller than a site's. A commercial suite has thousands of
  generated cases; ours have eight to eleven chosen ones. We accept weaker
  coverage in exchange for every case being explicable — and the content suite
  requires the suite to reject the stub, which a generated suite does not
  guarantee either.
- Every expected value is ours to get wrong, and three were. The oracle caught
  all three (§16).

## Alternatives considered

**Copy the problem statements and write our own tests.** The closest to winning,
because the statements are the slow part and the tests are the interesting part.
Rejected on licensing: LeetCode's terms prohibit reproduction of problem content
outright, and "we only copied the prose" is the part they are about. It would
also have forced a choice between matching their examples and matching our
grader.

**Link out instead of shipping text** — a prompt that is one line plus a URL.
Rejected because the tool is offline by design (PLAN.md §2), and because a
prompt that cannot be read without a network is not a prompt. It would also make
the exercise's content depend on a third party's edits.

**Use only public-domain sources** — Cormen's exercises, Project Euler, classic
textbook problems. Rejected as a solution to a problem it does not solve: the
*statements* in those books are still the authors', and the ones that are
genuinely free are phrased for a reader with the chapter in front of them.

**Generate prompts with an LLM from a list of problem names.** Rejected for the
same reason the notes exist: the explanation is the product, and a generated
explanation is indistinguishable from a restatement until someone is misled by
it. Writing the prompt is also how the discriminating test gets found, and that
step cannot be skipped without losing it.

## Revisit if

- Someone wants to ship an **importable content pack** (PLAN.md §13 parks one as
  a "content repository adapter"). The decision above is about what *this
  repository* ships; a pack someone else authors under their own licence is a
  different question, and the adapter boundary is where it would be answered.
- A genuinely permissively licensed problem set appears whose licence survives
  redistribution inside a tool like this one. Then the argument is about quality
  rather than legality, and the quality bar is in PLAN.md §9.

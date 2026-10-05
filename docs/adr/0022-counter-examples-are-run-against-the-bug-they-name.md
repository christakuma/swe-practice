# 0022 — Counter-examples are run against the bug they name

- **Status:** accepted
- **Date:** 2026-10-05
- **Phase:** 17 (the Blind 75 fill-in)

## Context

A kata's hidden tests are supposed to be *discriminating*: to reject a plausible
wrong answer, not merely an unimplemented one. `tests/content/test_katas.py`
says so in its own docstring, and names the gap — it proves `solution.py` passes
and `stub.py` fails, and cannot prove anything about a solution in between.

Phase 17 added 53 katas, each with an adversarial test or two written
deliberately against a named failure mode: "a solution that clamps the tally at
zero returns …", "a start-ordered greedy reports …". Those docstrings are
claims about code that was never written.

**Sixteen of them were wrong, in three kinds**, and the kinds are the whole
argument:

- **Seven wrong expected values** — `max_product([2, -5, -2, -4, 3])` written as
  120 when it is 24, `smallest_window("aBb", "ab")` as `"Bb"` when it is
  `"aBb"`, `best_haul([5, 0, 0, 5])` as 10 when a circle of four makes
  positions 0 and 3 neighbours, two in `fewest-intervals-to-remove`,
  `alien_order(["ba", "ca"])` as `"bca"`, and a level-order reading written
  unpadded. **The content suite caught every one of these immediately**, because
  the reference disagreed.
- **Six tests that could not fail, or did not discriminate.** Invisible to the
  content suite, because the reference passes them too. These are the ones this
  record exists for.
- **Three wrong prose claims** — a prompt example missing a combination, a
  prompt explaining a cell as reaching neither ocean when it reaches one, and a
  reference docstring asserting a statement-ordering bug that is not one.

The six are worth listing, because three of them were only found by a code
review *after* this ADR was first written — which is the strongest evidence the
decision below is load-bearing rather than tidy.

`find-a-word-in-a-grid` gained a counter-example meant to separate real
backtracking from a permanent `visited` set — a 3×3 ring of `A`s around a
central `B`, with the word `AAAB`. It reads as obviously discriminating. The
broken solution passes it. Brute-forcing every 2×2 and 2×3 grid found the actual
minimal case, a 2×2 `AA`/`AB`.

Two could not fail at all. A long-string palindrome test inserted a mismatching
character at the **exact centre** of a palindrome, which leaves it a palindrome.
An `insert-an-interval` test asserted a hand-counted length of
`25_000 + 1 + 25_000`, which is the very off-by-one the test existed to catch.

And three were **timing** claims that no longer held at the size chosen, all
three found by review. `implement-a-trie` claimed a scanning solution "does not
finish"; it finished in 5.0s against a 15s limit, so a `set` with a linear
prefix scan passed the kata whose entire subject is that it should not.
`count-palindromic-substrings` claimed the same of the cubic solution, which
finished in 5.4s. And `longest-palindromic-substring` claimed per-centre slicing
"turns quadratic into cubic", which is wrong arithmetic — `2n - 1` centres times
one `O(n)` slice is `O(n²)` — *and* undetectable, since CPython's slice is a
memcpy and even per-step slicing only reached ~3s.

That third kind is the one worth naming separately: **an asymptotic argument is
not a performance claim until the constant is measured.** `O(n³)` beats `O(n²)`
in the limit and not necessarily at the size you picked, and a wall-clock limit
tests the size you picked.

And one was a claim rather than a value: `best-time-to-buy-and-sell`'s reference
docstring asserted that updating the running minimum before recording the profit
permits a same-day trade and is a bug. It is not. The illegal trade is worth
exactly zero and the accumulator already floors at zero, so both orderings are
correct — which is a better lesson than the one asserted, and was only
discovered by brute-forcing every price list up to length seven.

The common factor: **for a problem whose whole point is a constraint you are not
used to, your intuition about examples is the thing under test.** The content
suite catches a wrong *value* immediately, because the reference disagrees. It
cannot catch a counter-example that happens not to discriminate, or an
assertion that cannot fail, because the reference passes those too.

## Decision

A content test that names a specific wrong solution is **executed against that
solution** before it is committed. Writing the buggy variant in a scratch script
and confirming it fails is part of authoring the test, not a later audit.

Where a kata's expected values are computed by hand, they are **machine-checked
against an independent oracle** — a second implementation with different failure
modes, usually the solution the prompt forbids — and the oracle is kept in the
test file as a sweep rather than discarded.

Where an expected value needs the same arithmetic as the code under test, it is
**not computed by hand at all**; the test compares against the oracle.

Concretely, in this phase: `find-words-in-a-grid` against the single-word search
over 380,100 (grid, word-list) pairs; `best-path-sum-in-a-tree` against a path
enumerator over 140,680 trees; `alien-alphabet-order` against a permutation
search over ~62,000 word lists; `median-of-a-stream` against
`statistics.median` at every prefix of ~140,000 streams;
`water-flowing-to-both-oceans` against a forward downhill search over 21,297
grids; `rebuild-a-tree-from-traversals` round-tripped through every tree shape
up to eight nodes.

## Consequences

**What it buys.** Nine defects that would have shipped, every one of them
invisible on the page. More importantly, the adversarial docstrings become
*true* — a solver reading "a solution that only tries character-centres returns
`c` here" is reading a verified fact, which is the difference between a teaching
note and a plausible-sounding one.

It also changed two katas for the better rather than merely fixing them. The
`best-time-to-buy-and-sell` docstring now makes a stronger point than the false
one it replaced: an impossible case that cannot win does not need excluding.
And `how-many-meeting-rooms` gained a bound its contract says is unreachable,
because the exhaustive sweep included degenerate intervals and found that a
zero-width meeting walks the sweep pointer off the end.

**What it costs.** Authoring time, mostly in writing oracles — a second
implementation per kata, which is real work and occasionally harder than the
solution. Runtime: the sweeps are the slowest tests in the content suite, and
one of them had to be trimmed when it pushed a file to eight seconds against a
ten-second limit, which is the kind of margin that passes locally and fails on a
loaded CI box.

And a cost worth naming because it is not obvious: the oracles are usually the
solutions the prompts **ban**. `fnmatch` for the wildcard trie, `sorted(a) ==
sorted(b)` for the anagram, sort-and-merge for interval insertion. Having them
in the test file is a standing invitation to read the tests and find the easy
answer — mitigated only by the tests being hidden, which is a property of the
harness rather than of the content.

## Alternatives considered

**Rely on the existing content suite.** It proves the reference passes and the
stub fails, which is the claim §11 is careful to limit itself to. Rejected
because it is exactly the claim that misses the six that matter: every one of
them left the reference passing. It did catch all seven wrong expected values,
immediately, which is the half it is good at.

**Require a counter-example per kata, declared as data.** Git scenarios already
do this — §5.4 has `counter_examples` in the schema, with the checks each must
fail. The nearest thing to winning, and rejected for now because it means
shipping a wrong solution per kata in the content directory, and because the
useful counter-examples here are *oracles over a swept input space* rather than
single inputs. A 2×2 grid is the minimal case only because 380,000 grids were
tried; a declared counter-example records the answer and not the search.

**Property-based testing (Hypothesis).** Genuinely attractive, and the right
tool for a larger input space than these katas have. Rejected because
exhaustive enumeration is *available* at these sizes and strictly better when it
is — "every 0/1 matrix up to 3×4" is a stronger statement than "200 random
ones", and it is reproducible without a seed. Worth revisiting if a future kata
has an input space too large to enumerate.

**Trust the author and review the prose.** This is what produced the sixteen
defects — though it is worth conceding that a review *did* find the last three,
which suggests prose review and this procedure are complements rather than
alternatives. What a review cannot do is find them reliably; these three
survived the phase that wrote the rule. The failure mode is specifically that the prose reads correctly; a
reviewer who could spot a non-discriminating counter-example by eye could have
written it correctly in the first place.

## Revisit if

A kata arrives whose input space cannot be enumerated or whose oracle would be
as hard to trust as the solution — a numerical problem with tolerance, or
something whose only reference is the thing being tested. At that point the
honest move is property-based testing with explicit invariants, and this ADR
should say so rather than pretending a sweep is available.

Also revisit if the sweeps come to dominate the content suite's runtime.
`tests/content/test_katas.py` is now the critical path under `--dist loadfile`,
having overtaken `test_scenarios.py` at ~162s, and the sweeps are most of the
growth. The fix would be to mark them and run the exhaustive tier separately
from the per-kata correctness tier, which is a real change to §11's two-tier
scheme and should be argued for rather than drifted into.

An earlier draft of this clause put that file at "240s serially". Three runs on
an idle machine gave 240s, 414s and ~500s, so the number is **400s give or take
a hundred** and a single measurement of it is not evidence. Worth leaving in the
record, because quoting one timing run as a fact is the same error as asserting
a counter-example without executing it — and this ADR managed both in the same
commit.

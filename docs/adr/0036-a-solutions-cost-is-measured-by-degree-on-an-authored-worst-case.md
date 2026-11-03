# 0036 — A solution's cost is measured, by degree, on a worst case the author writes

- **Status:** proposed
- **Date:** 2026-11-03
- **Phase:** none yet. Decided ahead of the phase that builds it, from a prototype
  and a sweep of the whole kata library

## Context

PLAN.md §7 compares the complexity a solver declares with the one the kata
expects, and never grades it: "static Big-O analysis of arbitrary code is not
something to pretend to do." That is still true. This record is about a
different thing: **measuring** how a solution's cost grows as its input grows.
Analysis claims to know the cost. Measurement observes it over a range of sizes
and says only what it saw.

The question was whether that observation is good enough to show a solver. A
prototype answered it on three katas (two-sum, longest-increasing-subsequence,
word-break), each with its reference and three solutions of known, different
cost, plus eight calibration functions whose cost is exact. That is 28
configurations, measured three times each. A sweep then measured all 245
references in the library (83 katas, 162 variants) using inputs derived from
ADR 0035's signatures alone, in three rounds, with the instrument fixed between
rounds. Every number below comes from those
runs. The scripts and raw results stay outside the repository.

**What an instrument can see, measured, not assumed:**

- **Counting `LINE` events does not count work.** CPython's `sys.monitoring`
  fires `LINE` when execution moves to a *different* line. A comprehension, a
  generator expression or `for x in xs: t += x` counts once however long it
  runs, so an O(n²) calibration function counted 4 lines at every n. The
  events that do count every iteration are `BRANCH` and `JUMP`. With `PY_START`
  and `PY_RESUME` for calls, the code between two events is straight-line and
  bounded by the length of the source. **That event count is proportional to
  the Python work done**, and it is exact: identical in all three runs, to the
  event.
- **Work done in C is invisible to any event.** `x in list`, slicing, `sorted`
  and `bisect` each look like one step. The wall clock does see that work.
  With the clock allowed to add a degree only when its slope beats the step
  count's by at least 0.75, the three solutions whose quadratic work runs in C
  were all caught. Their gaps were 0.93 to 1.12. The largest gap among cases
  that should *not* switch was 0.48.
- **A log factor inside C cannot be measured at all.** `sorted`, `bisect` and a
  sort-based two-sum timed at slopes of 1.09 to 1.19; genuinely linear code
  timed at 1.04 to 1.40. Step counts recovered O(n log n) exactly whenever the
  log was in Python (a hand-written merge sort, a hand-written binary search).
  An early version of the comparison reported log factors and told the LIS
  *reference* it was a log factor better than its own declaration.
- **Below about 100 µs a call, the clock measures the memory hierarchy.** The
  sweep's reference for the lowest common ancestor in a search tree takes 4
  steps at every size. Its time still rose 18x, because each timed call met a
  freshly built tree that no longer fitted in cache. Above that floor, rounding
  the clock's degree *down* was still necessary: `meeting-rooms` exits after
  three steps and spends its time in a C sort of 10⁵ tuples, which timed at
  slope 1.47.
- **Space needs two instruments.** `tracemalloc` peak, less the smallest size's
  peak (a fixed floor otherwise flattens a linear slope to about 0.5), sees the
  heap. It sees recursion only partly: nothing for the first ~500 frames, then
  about 32 bytes per frame as the interpreter allocates more stack chunks. A
  call-depth counter on the same events is exact. A wart that was not fixed:
  CPython caches the integers up to 256, so a list of small ints allocates
  nothing until n passes 256 and then jumps. That jump inflates a slope taken
  over the top three points, and it is behind both of the sweep's spurious
  O(n²) space verdicts (`edit-distance`, `fewest-cuts-into-palindromes`).

**What the prototype measured, with inputs written per kata:** time right to
the degree in **25 of 28** configurations, the same in all three runs. Two of
the misses do O(n³) character work in C and measured about n^2.4, because at
the kata's bound of 1,000 characters the cubic term has not taken over. The
measurement describes cost over the range the kata promises, not in the limit.
The third is an O(m) setup that is negligible next to an O(n²) loop at every
size the kata allows. Space was right in 26 of 28. A reference's whole ladder
took 0.2 to 1.8 seconds. A slow solution used its full ten-second budget and
still got the six to nine sizes a fit needs.

**The input is the hard part, and three of the prototype's own expected answers
were wrong about it.** A sort-based two-sum and a "sorted in C" calibration
function were labelled O(n log n). Both measured O(n), correctly: the inputs
were already in order or reversed, and Timsort handles runs in linear time. A
list-backed dictionary was labelled O(m) a lookup and measured the same as a
set, because the matching words were first in the list. **The worst case
belongs to the solution, not to the kata.** One parameter at a time also cannot
tell O(n·m) from O(n+m), because both are linear in m with n fixed. Growing n
and m together caught the list as quadratic.

**What the signature alone could measure** (the sweep, final run):

| outcome | references | why |
|---|---|---|
| a time verdict | 176 | |
| unsupported shape | 41 | 10 design katas (classes need a call sequence), 13 with nothing that grows, 6 dicts, 5 with two functions, 7 graph nodes, containers of nodes, or an unusual node constructor |
| invalid input | 25 | the reference raised: a `notes:` precondition the signature cannot carry ("exactly one pair adds up", `k` within the tree, edge endpoints below `n`) |
| no verdict | 8 | the step count *fell* as n rose: random data hit an early exit at some sizes and not others |
| too few sizes | 3 | output-sensitive searches that ran out of budget |

Of the 176 verdicts, **144 agree** with the declaration read with every size
variable growing, 23 are better and 1 is worse. Read strictly, only `O(n)`-shaped
declarations can be compared at all: 61 of the 176 are prose such as
`O(n * k^2) for a longest word of length k`. Every one of the 24 disagreements
traces to the input or the declaration, not to the instrument. Four were checked
by running the reference on the worst case the explanation names; the other 20
were classified by reading the code:

- **13: random input is not the worst case.** Random letters make every
  palindrome short; two random trees differ at the root. Running the four
  checked references on all-`a` strings, a true palindrome and two identical
  trees moved each one to **exactly** its declared degree (step slopes 1.97,
  1.98, 1.00 and 1.00, up from 1.00, 1.00, 0.00 and 0.00).
- **7: a variable the declaration names is bounded by the signature.** The
  alphabet, the longest word, the number of coins. Read as growing, `O(n · L)`
  is n²; the signature caps L at 20.
- **4: the declaration is output-sensitive or exponential**
  (`O(number of combinations * target / smallest)`), and cannot be compared by
  degree.

The space comparison found **four real defects in shipped content.**
`maximum-subarray`, `maximum-product-subarray`, `house-robber-in-a-circle` and
`largest-slice-sum-after-dropping-one` declare O(1) space, and each reference
loops over or passes along `numbers[1:]` or `houses[:-1]`, copying the list. All
four measured **exactly 8 bytes per element**: a list's pointer array.
`maximum-subarray`'s docstring says "Two running values, no array … which is
why this is O(1) space." Every such claim the library makes was written by
hand, and nothing has ever checked one. (All four now walk the list with
`itertools.islice`; their peak heap is flat from n = 1,000 to 100,000, where
it had been ~800 KB at the top.)

Writing the instrument found ten bugs in it, all invisible on reading: the
`LINE` event, the frame-stack accounting, a fitter that could not report O(1)
until it preferred the simplest class on a tie, sub-microsecond timing, the
heap floor, reusing one input across timed calls (it hung
`merge-two-sorted-lists`, whose first merge spliced its inputs together, and it
timed every in-place kata on its own output), building a fresh input for every
call (that ate the whole budget, and 49 references got fewer than four sizes),
redrawing the fixed parameters at each size (`coin-change-from-a-purse`
measured n^2.6 because its `amount` changed at every rung), and both clock
false positives above. That is [ADR 0022](0022-counter-examples-are-run-against-the-bug-they-name.md)
again, one level up: an instrument that has not been run against cases of known
cost is a guess about them.

## Decision

1. **A solution's cost is measured on submit and reported as advisory.** A
   third advisory `CheckReport`, `measured-complexity`, sits beside
   `declared-complexity`, and it can never fail a verdict. It does not run on a
   preview ([ADR 0013](0013-grade-on-save-is-a-preview.md)), because it costs
   seconds. The report is a three-way comparison: what the solver claimed,
   what the kata expects, and what was measured: *"grows like n² over
   n = 32 … 2,048; you declared O(n)."*
2. **Time is measured by counting control-flow events** (`BRANCH`, `JUMP`,
   `PY_START`, `PY_RESUME`) and fitting the counts. The wall clock may only
   **raise the result by a whole degree**: when its slope beats the step
   count's by at least 0.75, the top size takes at least 100 µs a call, and
   the clock's degree is rounded down. **A step count that falls by more than
   10% from one size to the next gives no verdict at all**, because the input
   has changed character.
3. **Space is the `tracemalloc` peak above the smallest size's, plus the maximum
   call depth**, reported separately. The declared degree is for auxiliary
   space, so the harness subtracts the returned value's deep size. *This last
   step was not prototyped.* The sweep counted outputs, and six of its 41 space
   disagreements are declarations that say "beyond the output".
4. **Results are compared by polynomial degree only, never by a log factor.**
   Any log factor ("O(n log n)") is reported as `O(n)/O(n log n)`. A
   declaration's degree is compared after rounding to the nearest whole
   degree.
5. **A kata opts in with an authored `measure:` block, and the inputs are
   code.** The prose `expected_time` and `expected_space` stay for the page.
   The block names which parameters grow together, the worst-case makers (each
   a function from `n` to arguments, in a sibling `measure.py`), and the
   declared `time_degree` and `space_degree` as numbers. Every maker is run and
   **the worst verdict is kept**, because the worst case belongs to the
   solution. A kata without the block shows no measurement. Nothing requires
   one.
6. **The signature-derived generator is a drafting tool, not a source.** As
   with ADR 0035's constraint migration, it writes a first `measure.py` that a
   person reviews. It cannot know a precondition, an alphabet or a worst case,
   and the sweep showed all three matter.
7. **A content test holds every opted-in kata to its block, in an exhaustive
   tier of its own** (a new marker, run before a push and in CI). The
   reference must measure at its declared degrees under every maker. A
   `slow.py` counter-solution must measure strictly worse under at least one,
   which proves the makers discriminate (ADR 0022). Step counts must never
   fall as n rises.
8. **Placement follows the existing boundaries.** The fitter, the verdict rules
   and the degree comparison are pure functions in `domain/complexity/`, under
   the coverage gate. The measuring code is a footer appended to the solution,
   like `tests/content/bounds_probe.py`, and run as a second process through
   the sandbox port, so `adapters/sandbox` is still the only importer of
   `subprocess`. The budget is ten seconds per submission, separate from the
   kata's time limit.

## Consequences

**What it buys.** A solver who declares O(n) for a nested loop sees "grows like
n²" beside the claim, measured on their own code. That makes PLAN.md §7's
reconcile-the-disagreement step concrete. It also gives the library its first
check of a stated cost: the sweep's four O(1) declarations that copy the list
were found in an afternoon, and nothing else would have found them.

**What it costs.**

- **Authoring.** A worst-case maker per kata, often two, plus a slow
  counter-solution, for up to 245 references. The draft covers the input shape
  for 176. The worst case, the preconditions and the counter-solution remain a
  person's work, which is why the block is opt-in.
- **Suite time.** Measuring a reference took 1.6 s at the median, 4.5 s at the
  90th percentile and 6.0 s at worst. All 245 took about six minutes serially,
  more with several makers each. That is why the test gets its own tier rather
  than joining `test_katas.py`, which is already the suite's critical path.
- **Submission latency.** Up to ten seconds more on a submit that measures.
  A slow solution always uses its whole budget.
- **What it cannot say.** A log factor inside C, and an asymptotic term that
  has not taken over within the kata's bounds. Two prototype solutions do O(n³)
  work and measured n^2.4. The report must say "over n = … to …", because that
  is all it knows.
- **Interpreter coupling.** The step count depends on which events
  `sys.monitoring` defines and when they fire. The project pins Python 3.13.
  The calibration functions have to be re-run before that pin moves.
- **It can be gamed.** `sys.monitoring.get_tool` shows that a probe is
  attached. For a practice tool that does not matter, and it is one more
  reason the measurement never grades.
- **The clock still sees the machine.** The escalation margin (0.93 against
  0.48) was measured on an idle machine, and CLAUDE.md records a 2.3x timing
  spread under load. If clock escalations become unstable, the exhaustive tier
  is where it will show.

## Alternatives considered

- **Derive every input from the signature, with no authored block.** The
  closest to winning, and the reason the sweep exists. It measured 176 of 245
  references and agreed with 144. It failed in exactly the places that need
  judgement: 25 references raised on inputs the signature allows and a note
  forbids, 13 measured below their declaration because random data is not the
  worst case, and 8 gave no verdict because the input changed character as it
  grew. A verdict that is wrong only when the input is unlucky is wrong in the
  way that teaches the wrong lesson. Kept as the drafting tool (decision 6).
- **Static analysis of the code.** Rejected for PLAN.md §7's reason, which the
  prototype did not weaken. The interesting costs live in what a call does,
  and `x in some_list` looks the same to a parser whether the list holds three
  items or a million.
- **Count `LINE` events.** Rejected after it counted an O(n²) comprehension as
  four lines at every n.
- **Count `INSTRUCTION` events.** Exact, and about 67x slower than an
  unmonitored run, against 44x for `LINE`, `JUMP` and `BRANCH` together. It is no more
  accurate about growth, because straight-line code between two control-flow
  events is a constant, and it is just as blind to C.
- **Time it, and nothing else.** With 25% noise, which is within this machine's
  spread under load, a synthetic check of the fitter named O(n) correctly in as
  few as 73% of trials, depending on the range of sizes, and named O(log n) in
  as few as 31%. The sweep's two clock false positives would also have been
  verdicts. The clock is kept only for what it alone can see.
- **Fit the heap with the same curve-fitter as time.** Rejected: dict resizing
  makes heap growth a staircase, and the fitter called O(n) structures
  O(n log n) and O(n²). The heap is bucketed by its top-of-range slope above a
  floor instead.
- **One generator per kata.** Rejected because the prototype's own sort-based
  two-sum measured linear on a list that was already in order. Makers are a
  list, and the worst verdict wins.
- **Make the measurement fail a submission.** Rejected. It is an observation
  over a range with a known blind spot, and the same verdict would hold a
  correct O(n log n) solution that sorts in C to a standard the instrument
  cannot apply.
- **Weight C calls by their argument size** (a `CALL` event, and a table of
  what `in`, slicing and `sorted` cost). Not prototyped. It would trade a
  degree-only verdict for a table that has to know every builtin, and the
  clock already catches the whole-degree cases.

## Revisit if

- **The Python pin moves.** Re-run the calibration functions first. 3.14
  deprecates the `BRANCH` event in favour of `BRANCH_LEFT` and `BRANCH_RIGHT`,
  and this record's step count is built on `BRANCH`. Check 3.14's
  documentation before relying on this note: it was not tested here.
- **Fewer than about a third of the katas have a `measure:` block a year after
  it ships.** Then the authoring cost was misjudged, and the drafted makers'
  agreement rate (144 of 176) becomes the argument for shipping drafts with a
  visible caveat.
- **The exhaustive tier shows clock escalations that differ between runs.**
  Then the 0.75 margin was an idle machine's number, and the clock should be
  dropped in favour of steps only, with C-level work declared out of scope.
- **A kata needs a log factor reported**, for example one whose whole lesson is
  O(n log n) against O(n). Then that kata's makers must make the log visible in
  Python, as the hand-written binary search did, and the block has to say so.

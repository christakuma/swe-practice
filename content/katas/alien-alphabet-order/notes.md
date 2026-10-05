# Alien Alphabet Order — the graph is the easy half

Revealed after grading. The problem is the classic one (LeetCode 269); the
wording above is ours, with one deliberate change: it demands the
**lexicographically smallest** valid ordering rather than any valid one, so the
answer is unique and gradable.

Once you see "topological sort", the sorting is routine — you have already
written it in [topological order](../topological-order/notes.md). Everything
hard here is upstream of that, in working out what the constraints actually
are.

## Extracting the constraints

Each adjacent pair of words yields **exactly one** fact: at the first position
where they differ, the earlier word's character precedes the later one's.

```python
for earlier, later in pairwise(words):
    for first, second in zip(earlier, later):
        if first != second:
            add_edge(first, second)
            break                      # <- everything after this is unconstrained
    else:
        if len(earlier) > len(later):
            return ""
```

**`break` is load-bearing.** Once the ordering is decided by an earlier
character, later characters tell you nothing. Read the whole pair and `["ab",
"ba"]` claims both `a < b` and `b < a` — a cycle invented out of thin air, so a
valid input reports `""`. `test_takes_only_the_first_difference_from_each_pair`
is that case.

## The prefix rule, which produces no edges at all

```
["abc", "ab"]  ->  ""
```

No alphabet sorts a word before its own proper prefix — length breaks the tie
in `strcmp` and no character ordering can override it.

This is the case most solutions miss **entirely**, and the reason is
structural: the pair generates *no constraint*, so a solution that only builds
a graph and sorts it sees an unconstrained alphabet and returns a perfectly
plausible answer. The failure is silent, and no amount of cycle-detection finds
it.

Worth generalising: **an input can be invalid in a way that adds no data.**
Validation that lives entirely inside the derived structure cannot see it. The
check has to happen where the input is read, which is the `else` clause of the
`for` — one of the few places a `for/else` genuinely reads better than the
alternative.

## Deduplicate the edges

The same constraint can be implied by many word pairs. Kahn's algorithm counts
in-degrees, so adding `a -> b` twice leaves `b` with an in-degree that never
reaches zero and a valid input reports `""`.

```python
if second not in successors[first]:
    successors[first].add(second)
    incoming[second] += 1
```

`test_handles_duplicate_constraints` covers it. This is a general hazard with
in-degree counting rather than a quirk of this problem — the count must be of
*distinct* predecessors.

## The min-heap, and why sorting the output does not work

```python
available = [c for c in characters if incoming[c] == 0]
heapq.heapify(available)
```

Taking the smallest *currently available* character at each step is the greedy
choice that builds the lexicographically smallest sequence.

It is worth being clear that this is not the same as sorting anything
afterwards. On `["ca", "ab"]` the constraint is `c < a`, and `b` is
unconstrained:

- plain sorted order `"abc"` is **invalid**;
- the smallest valid answer is `"bca"` — the unconstrained `b` goes first.

No post-processing of a valid order produces that. It comes from the choice
made at each step, which is why the queue has to be a priority queue.

(With a plain deque you get a valid order that depends on insertion sequence —
correct for the usual statement of the problem, and untestable, which is why
this version asks for the smallest.)

## Unconstrained characters still count

Every character appearing anywhere must appear in the output exactly once, even
if nothing compares it. `test_includes_unconstrained_characters` uses
`["acd", "bcd"]`, where only `a < b` is implied and `c` and `d` are never
compared at all. Seeding the graph from the *edges* rather than from the
characters drops them.

## On verifying it

The reference was checked against a brute-force oracle — try every permutation
of the alphabet, return the first under which the words sort — over about
**62,000 word lists**: every short list over three letters, every pair and
triple of three-character words, and 40,000 mixed-length lists over four
letters.

And one expected value in the test suite was wrong when written
(`["ba", "ca"]`, asserted `"bca"`, actually `"abc"`), caught by the content
suite. For a problem where the answer is a derived ordering, working the
examples by hand is unreliable — the oracle is the only honest check.

## What to take away

**When a problem reduces to a known algorithm, the reduction is where the bugs
are.** The topological sort here is textbook. The three real hazards — one edge
per pair, the prefix rule, distinct in-degrees — are all in translating the
input into the graph, and none of them is visible once you are looking at the
graph.

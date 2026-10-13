# 0027 — A kata's examples are source, and every one is run against the reference

- **Status:** accepted
- **Date:** 2026-10-12
- **Phase:** after Phase 20 (the statement pass)

## Context

The request was three things at once: *make sure the katas have proper
constraints, look over the questions and phrasing, and give me an examples tab
for correct input and output.*

Four things were true of the eighty-three katas going in.

**Examples lived inside the prompt**, as aligned text in a fence —
`two_sum([2, 7, 11, 15], 9)   ->  (0, 1)`. That read well and nothing ever ran
it. The workbench drew the prompt as one `pre`, so there was nothing to put on a
tab: the examples were not data.

**Constraints were adjectives.** "The list may be long", "amounts may be in the
thousands", "a few hundred cells on a side". A solver cannot choose between
`O(n log n)` and `O(n^2)` from an adjective, and nothing connected the words to
what the hidden suite actually passes.

**An example is a claim about the right answer**, printed where a solver
compares their own output against it. [ADR 0022](0022-counter-examples-are-run-against-the-bug-they-name.md)
is about claims nobody executed, and its cost there was a test that could not
fail. Here it is worse: a wrong example sends somebody debugging code that
works.

**Three surfaces show the task and only one of them is a web page.**
`practice solve --prompt` prints it and the tutor export hands it to a model
(ADR 0023). Anything moved out of the prompt is moved away from both unless
something puts it back.

## Decision

**`constraints:` and `examples:` are fields of the kata's spec**, optional in
the schema and required of every shipped kata by the content suite — the line
`domain/exercise.py` already draws between a representable exercise and a good
one.

**An example is two pieces of source in the kata's language.** `input` is a
snippet whose last line is an expression; `output` is an expression for the
value that line gives. An optional `explanation` is prose, and may hold a
drawing.

```yaml
examples:
  - input: |
      numbers = [0, 1, 0, 3, 12]
      move_zeroes(numbers)
      numbers
    output: |
      [1, 3, 12, 0, 0]
```

**`tests/content/test_katas.py` runs every one against the reference
solution**, in-process, and compares `repr` of the two values after turning any
`ListNode` or `TreeNode` into plain data. `repr` rather than `==`, because `==`
accepts `1` where the function returns `True`, `2` where it returns `2.0` and a
list where it returns a tuple. The output is evaluated against the module alone,
never against what the input left behind, so `output: numbers` cannot be
written.

**The workbench draws two tabs for a kata** — Prompt, with the constraints
listed under it, and Examples — as two radio inputs and CSS sibling selectors,
with no script. A scenario and a drill have neither field and keep the plain
heading.

**`Exercise.statement` is the task as plain text**: the prompt, then the
constraints, then each example. The CLI prints it and the tutor export carries
it, so the two surfaces without tabs show everything the page splits across
two.

**The bounds in each `constraints:` list were derived, not chosen.** A scratch
probe wrapped every reference solution, ran each hidden suite, and recorded the
shape of every argument passed — lengths, value ranges, emptiness, repeats.
Each stated bound is at or above what was observed, and each lower bound admits
what the suite really passes (an empty list, where it passes one).

## Consequences

**The page can say "checked" and mean it.** 317 examples across 83 katas run on
every content pass, in under a second for the lot. Four deliberate corruptions —
a wrong value, `1` for `True`, a list for a tuple, a tree with the wrong shape —
each failed with a message naming the example.

**The examples that existed were verified for the first time.** None was wrong.
That is a result rather than a non-event: it is the first time anything could
have said so.

**The lookover found what reading alone had not**, because the probe showed
what the suites pass and the prompts could be held to it.
`serialize-and-deserialize-a-tree` promised "a chain a thousand deep" and its
deepest chain is four nodes. `find-words-in-a-grid`, `count-connected-components`
and `is-this-graph-a-tree` are all tested on behaviour their prompts never
mentioned — an empty string in the word list, an edge from a node to itself.
And `meeting-rooms` and `how-many-meeting-rooms` were the same problem with the
same title and the same function name; the first is now the question the
Blind 75 has in that slot, which is the special case of the second.

**Constraints are stated and not enforced**, which is the cost. The probe was a
scratch script. A test added next month that passes an input outside a stated
bound fails nothing: the examples are checked on every run and the constraints
were checked once.

**A linked list's output reads as nested constructors.**
`ListNode(4, ListNode(3, ListNode(2, ListNode(1))))` is exact and pasteable and
not pretty. Tree examples carry a drawing in the explanation for the same
reason.

**Authoring has one trap, and the schema catches it.** `output: [0, 1]` is a
YAML list and `output: 3` a YAML integer. Both are rejected as "should be a
valid string", and the fix is a block scalar.

## Alternatives considered

**Leave the examples in the prompt and add a tab that repeats them.** Two
copies of every example, one checked and one not, which will disagree the first
time somebody edits either.

**LeetCode's notation** — `head = [1, 2, 3]` standing for a linked list,
`root = [3, 9, 20, null, null, 15, 7]` for a tree, `Input:` as named arguments.
The closest to winning, because it is what the tab's name suggests. Rejected
because it has to be *described* to a harness: a codec per node type, a rule
for a function that returns `None` and mutates its argument, a second format
for a class with methods, a third for a round trip. And what it displays is not
something a solver can paste into the file in front of them. A snippet covers
every shape with one rule — the value of the last line — and it is real code.

**Display text plus a separate executable check.** `input: "1 -> 2 -> 3"` for
the eye and `verify: ...` for the suite. That checks the `verify` and leaves
the display free to say something else, which is the unexecuted claim again
with an extra field.

**Validate the examples in the schema**, with `ast.parse`. Strictly weaker than
running them, and it would leave an author believing a file that passed
`practice validate` had examples that were *right*.

**Constraints as expressions the suite evaluates per call**
(`2 <= len(numbers) <= 10**5` checked against every argument the hidden tests
pass). This is the honest fix for "stated and not enforced" and it was not
built: it needs a quantifier for `numbers[i]`, and a constraint that reads as
`all(-10**9 <= x <= 10**9 for x in numbers)` is one nobody wants on the page.
Two fields — one to show, one to check — reintroduces the drift the examples
were designed out of. Left as the thing to do if a constraint is ever found to
be false.

**A script for the tabs.** The state is which of two panels is showing, which
is what a radio group holds and CSS can read. A scripted version would be a
fifth handler on a page with four, and would lose its state to the first htmx
swap that touched the column.

## Revisit if

- A stated constraint turns out to be false of the suite. That is the signal
  to build the enforced form, and to accept its cost.
- A second kata language arrives. The harness executes Python; `Example` and
  the schema do not know that, which is the half of this that was designed to
  survive the change.
- Examples want to be *run by the solver* — a "Run" beside "Submit" that grades
  only the examples. Everything needed is already data.

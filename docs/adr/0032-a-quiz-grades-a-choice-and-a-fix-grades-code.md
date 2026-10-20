# 0032 — A quiz grades a choice from a closed set, and a fix question grades code

- **Status:** accepted
- **Date:** 2026-10-19
- **Phase:** 25

## Context

A user asked for general engineering questions rather than more data
structures or tools: how to deal with a deadlock, what to do when a service is
slow. Asked whether they wanted to write code for each, they said no. They
wanted **a quiz, with a moment here and there to fix something small in a
file**.

That is the first request this project has had whose answer is not an
artifact, and the project's founding decision is against it. ADR 0003 grades
the end state and refuses to grade *the answer text*, because text has no
oracle: `git reset` is right or ruinous depending on what it is reset to, and
nothing short of running it can tell. §13 lists "system design drills" as
parked behind the same test: *can it be graded offline, on both platforms,
from declarative assertions?*

So the question this ADR answers is whether a quiz can be graded honestly at
all, and if so, on what condition.

## Decision

**A fifth kind, `quiz`, on one condition: every answer is a choice from a
closed set, a line, an order, or code.** Nothing is ever typed as prose. A
choice from a closed set has its answer fixed when the question was written,
so grading it is a set comparison, and ADR 0003's objection, that there is no
oracle for text, does not apply to it. Where an answer *is* an artifact, the
core bet comes back unchanged: a **fix question**'s answer is code, and a
hidden suite grades what the code does.

- **Five formats.** `single`; `multiple`, graded on the **exact set** so that
  ticking everything is not a strategy; `line`, one line of a numbered
  snippet; `order`, every step placed; and `fix`.
- **The answer sheet is the one editable file**, `answers.md`, which the web
  form writes and a solver at a terminal edits by hand. That kept the kind one
  clause in `editable_source`: `practice submit --source`, the tutor export
  and the MCP server took it unchanged. The key lives on the spec, in
  `exercise.yaml`, and never reaches the workspace.
- **The sheet is parsed in the domain, by hand.** Whether a choice was right
  is the whole verdict, so it belongs under the coverage gate, and the domain
  imports no third-party parser. The grammar is a line per answer and a
  fenced block under a heading per fix; everything else is ignored.
- **A fix is a question, not a separate exercise.** The suite runs through
  the kata runner (the same instance, so the same lock), one check per test,
  with ids `<question>/<test>`. Its counter-examples are code files, each
  required to fail exactly the tests it names (ADR 0022).
- **A failure says why the chosen option is wrong, never which is right.**
  A failed submission is a logged try (ADR 0029), so a second submission is
  a second attempt at the reasoning rather than a copy. The finished attempt,
  passed or conceded, shows every answer and every explanation, and so does
  the tutor export once there is a verdict (ADR 0023's rule, applied).
- **Option order is shuffled per attempt** by a hash of the attempt and the
  option, so a reload draws the same page. The plain-text statement cannot
  shuffle, so an `order` question is authored out of order, and the content
  suite holds that.

## Consequences

**The content suite gained a half no other kind has: rules about whether a
question gives itself away.** No option id may name its verdict (`correct`,
`wrong`, `best`...), no select-all may be answered by selecting all, no order
may be listed in its own order, the right option of a single choice may not
sit in one position more than half the time, and it may not be the strictly
longest, or the strictly shortest, more than half the time.

**The length rule failed the first draft, 21 questions out of 28.** The right
option was the strictly longest in three quarters of the single-choice
questions. That is the tell every quiz writer leaves: the careful, qualified
sentence is the one an author writes for the answer they believe in, and the
distractors get one clause each. The fix was to trim the right answers to a
claim and leave the reasoning in their `why`, which is where it is read; the
library now has the right option longest in 6 of 28 and shortest in 4. The
rule checks both ends because trimming is exactly how the opposite tell is
made.

**"Every question carries its own context" is a test, because it was the
user's requirement.** A question is drawn in a fieldset of its own and has to
be answerable from what is in front of it: the lock dump, the trace, the
rule. A question that leans on the ticket three screens up fails
`test_every_question_carries_its_context`.

**Two things nothing type-checks needed an edit**, the third time a new kind
has found these (ADR 0019, ADR 0030):

1. **The first screen.** `start-here` is the dashboard's six rows and must
   offer every kind; Phase 22 had written down that a fifth kind would take a
   git or kata row. Git gave one up: `amend-the-last-commit` moved to the head
   of `git-foundations`, where it is the first lesson anyway.
2. **The tutor content suite** checks that a graded attempt's bundle contains
   every explanation the exercise has. A quiz's explanations were on the page
   and not in the bundle until `_notes` carried the key.

**One finding from the browser that no test had.** Prose context authored as
a literal block (`|`) keeps its hard line breaks, and `pre-wrap` in a narrow
column wraps them again, so every sentence came out ragged. Prose contexts are
folded scalars now; dumps and tables keep their breaks, and the four that mix
the two use an indentation indicator so the dump lines are kept verbatim
inside a folded block.

**What this kind cannot do**, stated so nobody assumes otherwise:

- It cannot tell whether the solver *understood*. A guess that lands is a
  pass. The exact-set rule and the per-attempt shuffle make guessing worse
  than reasoning, and the logged tries make it visible; neither makes it
  impossible.
- It cannot catch a distractor that is right in some circumstance the author
  did not think of. That is the quiz form of a grader failing a correct
  answer, and the only defence is the one CLAUDE.md asks of every kind:
  argue for each wrong option before shipping it. Every option's `why` has to
  say when it fails, which is that argument written down.
- A fix's suite can only see what it was written to see. Each one was run
  against the answers its prompt rules out, and the ones a prompt leaves open
  were run too (`sorted(..., key=id)` passes the lock-order suite; a
  try-lock-and-back-off answer fails it, because the prompt asks for an
  order).

## Alternatives considered

**Write the scenarios as code exercises, graded by simulation.** The first
plan for this phase: a deterministic harness (a virtual-clock event loop,
instrumented locks, fakes with latency) and a service file to fix. It keeps
ADR 0003 whole, and it was what this ADR's author proposed. The user declined
it: they wanted to practise the judgement, not to write a service each time.
It survives in miniature as the fix question.

**Free-text answers graded by keywords or a model.** Rejected by ADR 0003
for the reason it gives about command text: a keyword passes an answer that
mentions the right word and is wrong, and a model-graded answer is a verdict
nobody can reproduce, offline or otherwise.

**Flashcards on the review scheduler.** The project already schedules
reviews, and a card per concept would have been cheap. It grades nothing: the
solver marks their own answer. A quiz question is a card with a key.

**The fix step as a separate exercise offered after the quiz**, as a variant
is offered under its base (ADR 0028). This was in the plan shown to the user.
It would have needed a second relation beside `variant`, a second unlisted
kind of exercise and a second way of reaching one. A question whose answer is
code needs none of those: it is one more report in one verdict, and the
attempt stays one attempt.

**YAML for the answer sheet.** It would have needed no parser of our own.
But a fix's code inside a YAML block scalar has to be indented by two more
spaces and kept there, which is the wrong thing to ask of someone editing
Python, and the domain would have taken its first third-party import.

**Grade-on-save for a quiz**, as own-editor mode gives a kata (ADR 0013). A
verdict on every save lets a solver flip answers until the page turns green,
with no try recorded. The quiz is drawn as a form with no own-editor button;
a sheet edited elsewhere is submitted with `practice submit --source`, and
every submission is a logged try. In ADR 0020's terms this withdraws an
affordance and contains nothing: the own-editor endpoint does not refuse a
quiz, so a hand-written POST would still get previews. Refusing it would be
a rule in `RevealSolutionFile` about one kind, and nothing reaches it today
but that request.

## Revisit if

- **A question needs an answer that is none of the five formats**, a number
  typed in or a word filled into a blank. Either can be graded exactly (a
  number within a tolerance, a word from a closed set), and either would be a
  sixth format arriving with the question that wants it (§13).
- **A fix needs a language other than Python.** The kata runner speaks only
  Python, which is the one place `FIX_LANGUAGE` is decided.
- **Quizzes grow past what the length and position rules can see.** They are
  library-wide proportions, and a library of eighty quizzes could hide a
  pattern inside one track that the total dilutes. The rule would then move
  to per-track.
- **The user wants the fix questions bigger.** At some size a fix is a kata
  with a ticket on top, and the first plan, a simulation harness, is the
  thing to reopen.

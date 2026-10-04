# 0016 — The demo is generated from captured output, not recorded

- **Status:** accepted
- **Date:** 2026-10-03
- **Phase:** Phase 12 — Polish and portfolio artifacts

## Context

PLAN.md §11 asked Phase 12 for "a README with the architecture diagram and a
demo GIF". The GIF is the convention and there is a reason for it: a README that
shows the thing working is worth more than a README that describes it, and this
project's whole argument is a *verdict* — the moment where the content check
passes and the ancestry check does not. That is a thing to watch happen.

Three constraints meet at that requirement.

1. **A GIF needs a recording tool and an encoder.** `asciinema` plus
   `agg`, or a screen recorder, or Pillow. None is installed and none can be
   added: `uv.lock` is resolved once from a dependency set declared in full at
   Phase 0, deliberately, so that every later phase is a code change only. A
   demo artifact is not a reason to reopen that.

2. **A GIF of a terminal is a picture of text.** It cannot be selected,
   searched, diffed, or read by a screen reader, and it does not reflow. The
   README's claim is a specific verdict with specific wording in it; a reviewer
   who wants to check that the verdict in the README is the verdict the tool
   actually prints has nothing to check it against.

3. **A recording goes stale silently.** The notes and the check labels in
   `content/` are the product (ADR 0009) and they get edited. A recorded GIF
   keeps showing the old wording until somebody notices, re-records, and
   re-encodes — which is enough friction that nobody does.

## Decision

**`docs/demo/session.txt` is the captured stdout of a real
`practice solve git/revert-a-pushed-commit -c my-attempt.cmds`, and
`docs/demo/render.py` draws it as an animated SVG at `docs/demo.svg`.**

The renderer is ~200 lines with no dependency, hand-rolled in the same spirit as
the progress charts in `interface/web/charts.py`. It colours lines by the
prefixes the CLI prints — `  ok   `, `  FAIL `, `  note ` and the continuation
indent — reading them off the output rather than importing the formatter,
because a demo generated from the code that produced it could not catch that
code changing.

Two properties are load-bearing:

- **It degrades to the complete transcript, not to an empty box.** Every line is
  authored with `opacity="1"` and hidden by the stylesheet. A renderer that
  strips CSS — a Markdown preview, an editor, a sanitiser — shows the whole
  session as a static terminal. The opacity is stated twice on purpose.
- **Whitespace is preserved twice over.** The markers the colouring keys on *are*
  the indentation, so it cannot be turned into an `x` offset:
  `xml:space="preserve"` is an attribute a stylesheet sanitiser cannot drop, and
  `white-space: pre` covers renderers that honour the CSS property instead.

Updating the demo is re-running the command and re-running the script.

## Consequences

**What it buys.** The transcript is text: selectable, searchable, diffable in
review, and readable aloud. The demo is regenerated rather than redrawn, so
keeping it honest is two commands rather than a recording session. It is 10 KB
rather than a megabyte, it is covered by the repository's LF rule like every
other text file, and it needs nothing that is not already installed.

**What it costs.**

- **Nobody can verify the capture without re-running the command.**
  `session.txt` is asserted to be real output; a committed text file is exactly
  as forgeable as a GIF is, and this ADR is the only thing saying it is not.
  The mitigation is that re-running it is one command, printed in the README.
- **The animation depends on CSS inside an SVG**, which some renderers strip and
  some proxies re-encode. That is why the static fallback exists, and the
  fallback is the reason this is an acceptable risk rather than a gamble.
- **One palette, dark only.** A theme-aware SVG would need a
  `prefers-color-scheme` media query, which is the first thing a sanitiser
  removes and which follows the *image's* context rather than the page's on
  GitHub. A terminal that looks like a terminal on both themes is the safer
  answer and it is a compromise.
- **It is still a second artifact to keep current.** Generated is not automatic.
  Nothing fails the build if `session.txt` changes and `demo.svg` is not
  re-rendered.

## Alternatives considered

**Record a real GIF.** The thing that was asked for, and rejected on the
dependency: adding `asciinema` and `agg`, or Pillow, to produce one image means
re-resolving a lock file that is deliberately resolved once. If the constraint
were only about tooling this would be the right answer, but points 2 and 3 above
hold even with the tools installed.

**A static SVG or PNG of the final screen.** Cheapest, and the closest to
winning. Rejected because the thing worth demonstrating is a sequence — commands
run, then a verdict lands — and a still frame of the end state is what the
README's fenced code block already was. It would have been a format change
rather than a demo.

**Keep the fenced code block and call it done.** Honest, free, and what the
README had. Rejected because Phase 12's job is the portfolio artifacts, and the
argument for a moving demo (you watch the FAIL arrive) survives every other
objection here.

**Generate the SVG as part of the test suite, and fail the build when it is
stale.** Genuinely tempting — it is what `practice fixtures --check` does for
fixtures, and it would fix the last consequence above. Rejected on the boundary:
`docs/demo/render.py` is a script under `docs/`, not a package, and a test
importing it would put a cross-directory import into a suite whose whole
argument is about enforced boundaries, plus `render.py` into mypy's path for one
assertion. The cost is a stale picture; the cost of the fix is a hole in the
rule that catches real things.

**Screenshot the web app instead.** A real picture of the real product, and a
reasonable thing to add later. Not a substitute: the verdict is the argument,
and the verdict reads better as text than as a browser window.

## Revisit if

- **A recording tool arrives for another reason** — an end-to-end suite that
  captures video, say. Then the cost of a GIF is already paid and only points 2
  and 3 are left to argue, which is a much weaker case for this decision.
- **The demo goes stale in a way anybody notices.** Then the staleness check is
  worth the boundary cost after all, and the honest shape is a content test that
  runs the command and compares, not a unit test that imports a script.
- **GitHub stops animating CSS inside an SVG.** The fallback keeps the README
  correct, but the decision is then buying nothing over a static image and
  should become one.

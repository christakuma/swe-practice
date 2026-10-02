# 0010 — CodeMirror 5 over 6, to avoid an npm build step

- **Status:** accepted
- **Date:** 2026-10-02
- **Phase:** 7

## Context

A kata is solved by writing Python, so the workbench needs a code editor: syntax
highlighting, line numbers, and indentation that does not fight the language. A
bare `<textarea>` is usable and genuinely unpleasant — it is the one widget in
this app that someone spends fifteen minutes inside.

Three constraints, all from decisions already made.

**Everything is vendored, and there is no build step.** PLAN.md §8.2 and
[ADR 0007](0007-htmx-over-a-single-page-app.md): assets are downloaded once,
pinned by hash and committed, and the whole toolchain is `uv`. Anything that
arrives as ES modules needing a bundler brings npm with it.

**One language today, maybe two ever.** The library ships Python katas.
§15's third open question — kata languages beyond Python — concludes it is worth
it only if the author interviews in TypeScript. An editor whose extensibility is
its selling point is being bought for a flexibility nobody has asked for.

**CodeMirror 6 is the current, maintained line, and 5 is in maintenance mode.**
This is not a case where the old version is also the recommended one. CM5 gets
security and compatibility fixes and no features; CM6 is where the project's
attention is.

## Decision

Vendor **CodeMirror 5** — `codemirror.min.js`, `codemirror.min.css` and the
Python mode — as three committed files, pinned by SHA-256 in
`practice/interface/web/vendor.py` and verified by a test that reads what is on
disk.

The editor is instantiated in one template, over one textarea, with four options.
Nothing else in the app knows it exists.

## Consequences

**What this buys.** Three files, dropped in, working: 187 KB of committed assets
and no `package.json`, no bundler, no `node_modules`, no build output to review in
a diff. A second language is one more vendored mode file and a `language:` field
in an exercise's YAML — the mode name is already read from `KataSpec.language`
rather than hardcoded, so §15 Q3 costs a download and nothing else.

**What it costs.**

- **A maintenance-mode dependency at the centre of the one screen people use.**
  If CM5 stops receiving fixes, or a browser change breaks it, there is no
  upstream to wait for.
- **Accessibility and mobile are weaker than CM6's**, which rebuilt both
  deliberately. Single-user desktop tool, so this is a cost that is currently
  being paid by nobody — which is not the same as it not being a cost.
- **No access to CM6's extension ecosystem**, including the collaborative-editing
  and linting integrations. Nothing here wants either.
- **It is a one-way-ish door for the *next* editor feature.** Inline diagnostics
  from a failed grading run, say, would be written against CM5's API.

**What keeps the cost contained**, and this is why the tradeoff is acceptable
rather than merely cheap: the editor is referenced from exactly one template and
one manifest entry. §13 already names this — *"isolated to one template; CM6 +
esbuild is a contained swap if needed"* — and that is now literally true rather
than a forecast.

## Alternatives considered

**CodeMirror 6 with esbuild or Vite.** The honest modern choice, and rejected on
the toolchain rather than on the editor: it needs a bundler, which means npm in a
`uv` project, a `node_modules` nobody vendors, and a committed bundle that cannot
be reviewed. It also breaks the property that `uv sync` is the entire setup on
both platforms, which is a real cost for a tool whose point is to be runnable
offline on a laptop.

**A prebuilt CM6 bundle from a CDN, vendored.** Avoids the build step by letting
someone else run it. Rejected because the vendored artifact would then be
*someone's build* of CM6 rather than a release of it — pinned by hash, which is
the mechanism this project uses, but to bytes whose provenance is a third party's
CI run rather than a published file.

**Monaco.** The editor from VS Code, and far more capable than either. Rejected
on size and shape: megabytes of assets, a web-worker architecture, and an AMD
loader that wants configuring. Every one of those is a problem specifically
because the assets have to be committed and served from disk.

**Ace.** Close to CM5 on every axis that matters here — single file, no build,
drops in. Rejected narrowly: CM5's mode files are the smaller unit for adding a
language, and CM6 existing means CM5 has a documented migration path if this
decision is reversed, which Ace does not have in the same form.

**A plain `<textarea>` with no editor at all.** Costs nothing and ships now.
Rejected because the editor is also what makes the §15 Q1 merge-conflict exercises
possible: the virtual `write` command takes file content as a single argv element,
so it cannot express multi-line content, and a real editing surface is probably
*required* for that family rather than optional. Shipping no editor would be
deferring that decision into a phase that depends on it.

## Revisit if

- CM5 stops receiving fixes, or a browser change breaks it. This is the expected
  trigger, and the one the containment above is insurance against.
- The project acquires an npm toolchain for an unrelated reason. The main argument
  against CM6 is the build step; if something else has already paid for it, this
  decision was bought with a cost that no longer exists.
- A third kata language lands, or the editor is asked for something CM5's API
  cannot express — inline diagnostics, multi-file editing, collaborative cursors.
  One of those is a workaround; three is a different editor.

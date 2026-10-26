# 0034 — Monaco, vendored and trimmed, replaces CodeMirror 5

- **Status:** accepted (supersedes [ADR-0010](0010-codemirror-5-over-6.md))
- **Date:** 2026-10-26
- **Phase:** 27

## Context

ADR 0010 chose CodeMirror 5 so that the project would not grow an npm build
step, and wrote down what that cost: "a maintenance-mode dependency at the
centre of the one screen people use". The user has since said the product should
be polished, and the editor is where that shows: Tab inserted a tab character,
nothing closed a bracket or matched one, there was no find, and the editor sat
in a fixed 26rem box in a vertical page. The trade ADR 0010 left open was
taken.

The constraint that did not move is §8.2: every asset is vendored, hash-pinned
and served from disk, with no CDN and no build step in the shipped package.
That excludes CodeMirror 6 as ADR 0010 found (ESM, needs a bundler to produce
a loadable file), and it decides what "trimmed Monaco" has to mean.

## Decision

1. **Monaco 0.52.2**, vendored under `static/vendor/monaco/`, replaces
   CodeMirror on every page that edits code: kata, SQL drill, container
   definition and a quiz's fix question. Two engines is worse than either, and
   `tests/web/test_editor_component.py` holds the pages to one.
2. **Pinned as a directory.** `vendor.VendoredTree` records the tarball URL,
   the ten members kept and one hash over every file's path and content hash.
   The tarball is read by member name and written by the downloader, never
   extracted. A stray file in the directory fails verification.
3. **A textarea is the contract.** `partials/code-editor.html` renders
   `<textarea data-code-editor="<language>">`; `static/editor.js` mounts Monaco
   beside it and keeps the two equal. The handle the workbench's own script
   holds, `getValue()` / `setValue()`, exists before Monaco has loaded and
   answers from the textarea until it has. Monaco is fetched only if a page has
   such a textarea.
4. **Completion is off.** Practice, not an IDE: autocomplete answers the
   question the exercise is asking. Find, bracket matching, auto-indent,
   closing brackets and quotes, and Ctrl+/ stay. The document is LF.
5. **The layout is a separate decision with the same ADR** because it is what
   the larger editor is for: an open kata or drill is prompt-beside-editor
   with a draggable, keyboard-operable divider remembered in `localStorage`.

## Consequences

- The wheel grows by about 4.4 MB (against CodeMirror's 0.3 MB), and a first
  kata page fetches roughly 4 MB from disk. On loopback that is not a wait.
- The dependency at the centre of the one screen is now actively maintained.
- Monaco touches the DOM heavily, so everything the suite can say about typing
  is a statement about configuration; the rest was driven in a browser and is
  recorded in PLAN.md §16.
- Adding a language is a tokenizer file added to `_MONACO_MEMBERS` and a new
  hash, which is cheaper than it was with CodeMirror (no template change).
- The page is more fragile to a failed load than a textarea, which is why a
  textarea is still underneath: if Monaco never arrives the page works.

## Alternatives considered

- **CodeMirror 6 with a committed build.** The closest alternative and the one
  ADR 0010 refused: a bundler's output committed as a vendored file. It is a
  smaller payload than Monaco and a nicer library to embed. Rejected because
  "the vendored file is the output of a build nobody can reproduce from the
  manifest" breaks the claim that a hash pins something reviewable. It was
  the smaller and tidier library to embed, and that is a cost of this choice.
- **Monaco, latest, whole.** Rejected twice over: the newest releases' ESM
  layout makes `editor.main` import a 7 MB TypeScript worker and three others
  statically, so they cannot be dropped; and the full package is 25 MB of
  languages nothing here edits.
- **Monaco's ESM build through a bundler in CI.** The same objection as CM6.
- **Staying on CodeMirror 5 and adding addons.** Closing brackets, matching and
  comment toggling all exist as addons, and it would have been a smaller
  change. Rejected because the point was a polished editor, and the library
  ADR 0010 already called legacy was the cost being paid.

## Revisit if

- A Monaco release restores a trimmable layout, which would let the pin move
  past 0.52.
- The wheel size becomes a complaint, at which point the question is whether
  the tokenizers can be loaded lazily from a smaller core.
- Monaco is dropped by its maintainers or becomes unfit to load offline.

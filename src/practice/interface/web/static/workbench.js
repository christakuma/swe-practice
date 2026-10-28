/*
 * The divider between a kata's prompt and its editor.
 *
 * **The script only moves a number.** The layout is one grid rule in `app.css`
 * whose first column is `var(--split)`; dragging sets that property on the grid
 * and nothing else, so the stacked layout below 900px -- where the divider is
 * not drawn and the rule is overridden -- needs no script awareness at all.
 *
 * Pointer events with capture, not mouse events: capture is what keeps the drag
 * alive when the pointer crosses the editor, which would otherwise swallow it.
 * The arrow keys move it too, because a splitter you can only drag is a feature
 * that is missing for anyone not holding a mouse.
 *
 * Where it was left is remembered in `localStorage`, behind a try: a private
 * window throws on access, and a divider position is not worth a broken page.
 */
(function () {
  "use strict";

  var grid = document.querySelector(".workbench.editing");
  var bar = document.getElementById("divider");
  if (grid === null || bar === null) {
    return;
  }

  var KEY = "practice.workbench.split";
  var MIN = 256;       // the prompt column cannot be dragged away
  var EDITOR_MIN = 384; // and neither can the editor
  var STEP = 24;

  // What the user chose, kept apart from what the window currently allows: the
  // clamp in `apply` is for this width of window, and reading it back would
  // replace the choice with the clamp.
  var wanted = null;

  function bounds() {
    return { min: MIN, max: Math.max(MIN, grid.clientWidth - EDITOR_MIN) };
  }

  function apply(width) {
    var limit = bounds();
    var clamped = Math.round(Math.min(limit.max, Math.max(limit.min, width)));
    grid.style.setProperty("--split", clamped + "px");
    bar.setAttribute("aria-valuemin", String(limit.min));
    bar.setAttribute("aria-valuemax", String(limit.max));
    bar.setAttribute("aria-valuenow", String(clamped));
    return clamped;
  }

  function current() {
    return document.querySelector(".workbench.editing > .prompt").getBoundingClientRect().width;
  }

  function save(width) {
    try {
      window.localStorage.setItem(KEY, String(width));
    } catch (error) {
      // the divider still moved for this page
    }
  }

  try {
    var stored = parseInt(window.localStorage.getItem(KEY), 10);
    if (stored > 0) {
      wanted = stored;
    }
  } catch (error) {
    // no remembered position; the stylesheet's default stands
  }
  // Stacked, the divider is not drawn and the prompt is as wide as the page;
  // reading that width back would replace the remembered one with the page's.
  function stacked() {
    return bar.offsetParent === null;
  }

  // With nothing remembered, the stylesheet's default is the choice -- the
  // width it asks for, not the width laid out. Read off the page, that is
  // already squeezed in a window just past the breakpoint, or clamped after a
  // narrow one, and widening the window would never undo it.
  function stylesheetDefault() {
    var value = getComputedStyle(grid).getPropertyValue("--split-default").trim();
    var number = parseFloat(value);
    if (/rem$/.test(value)) {
      return number * parseFloat(getComputedStyle(document.documentElement).fontSize);
    }
    return /px$/.test(value) ? number : current();
  }

  function settle() {
    if (wanted === null) {
      wanted = stylesheetDefault();
    }
    apply(wanted);
  }

  if (!stacked()) {
    settle();
  }

  bar.addEventListener("pointerdown", function (event) {
    bar.setPointerCapture(event.pointerId);
    bar.classList.add("dragging");
    grid.classList.add("is-dragging");
    event.preventDefault();
  });

  bar.addEventListener("pointermove", function (event) {
    if (!bar.hasPointerCapture(event.pointerId)) {
      return;
    }
    apply(event.clientX - grid.getBoundingClientRect().left);
  });

  function release(event) {
    if (!bar.hasPointerCapture(event.pointerId)) {
      return;
    }
    bar.releasePointerCapture(event.pointerId);
    bar.classList.remove("dragging");
    grid.classList.remove("is-dragging");
    wanted = apply(current());
    save(wanted);
  }

  bar.addEventListener("pointerup", release);
  bar.addEventListener("pointercancel", release);

  bar.addEventListener("keydown", function (event) {
    var delta = { ArrowLeft: -STEP, ArrowRight: STEP }[event.key];
    if (delta === undefined) {
      return;
    }
    event.preventDefault();
    wanted = apply(current() + delta);
    save(wanted);
  });

  // A window narrowed after a wide drag must not leave the editor a sliver.
  window.addEventListener("resize", function () {
    if (!stacked()) {
      settle();
    }
  });
})();

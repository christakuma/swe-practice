/*
 * The console's keyboard: history on the arrow keys, completion on Tab.
 *
 * **History is read from the transcript, not kept.** Up walks back through the
 * lines the page is already showing (`#console-log .line`), which the server
 * rendered from the attempt's own log. So history survives a reload, a second
 * tab and commands run yesterday from `practice resume --commands`, for the
 * reason the transcript itself does (`partials/console.html`), and there is no
 * second record to disagree with the first. A refused line is in it until the
 * page reloads, as a shell keeps a mistyped command: the line you got wrong is
 * the one you want back to fix. It is not in the attempt's log, so a reload
 * drops it, along with its entry in the transcript. A run of the same line
 * counts once, which is what zsh and fish do and bash does with `ignoredups`.
 *
 * Up from a half-typed line keeps it as a draft, and Down past the newest entry
 * brings it back, so recalling something to look at it never costs what you
 * were typing.
 *
 * **Completion asks the server, every press** (`CompleteCommandLine` has the
 * argument). One match fills the word in; several fill in what they share and
 * list the rest below the input, as zsh does on the first press rather than
 * bash's second. An answer that comes back after the line has changed, by
 * typing, by Up or Down, or by running it, is dropped rather than written over
 * the line you now have.
 *
 * **Tab completes whenever the line has text in it**, and moves focus as usual
 * when it does not. Shift+Tab always moves focus, and Enter runs the line, so
 * a keyboard user who tabs into the console can always leave it (WCAG 2.1.2,
 * no keyboard trap). Escape closes the list. The list is never `hidden`, only
 * emptied, because a live region that is not rendered when it fills is one
 * most screen readers never announce.
 *
 * The URL rides on the script tag, as `in-front.js`'s does, so the file has no
 * templating in it and `tests/web/test_console_script.py` runs it as served.
 */
(function () {
  "use strict";

  var url = document.currentScript.getAttribute("data-complete-url");
  var input = document.querySelector(".console-form input[name=line]");
  var list = document.getElementById("console-completions");
  if (input === null || list === null || !url) {
    return;
  }

  // Where Up has got to, counted back from the newest line; null when the
  // input holds the draft rather than a recalled line.
  var back = null;
  var draft = "";
  // Bumped by every keystroke, so an answer can tell it is stale.
  var typed = 0;

  function history() {
    var lines = [];
    var found = document.querySelectorAll("#console-log .entry .line");
    for (var i = 0; i < found.length; i += 1) {
      var line = found[i].textContent.replace(/^\s*\$\s*/, "").trim();
      if (line && line !== lines[lines.length - 1]) {
        lines.push(line);
      }
    }
    return lines;
  }

  function show(value) {
    typed += 1;
    input.value = value;
    input.setSelectionRange(value.length, value.length);
  }

  function recall(step) {
    var lines = history();
    if (back === null) {
      if (step > 0 || lines.length === 0) {
        return;
      }
      draft = input.value;
      back = 0;
    } else {
      back -= step;
    }
    if (back < 0) {
      back = null;
      show(draft);
      return;
    }
    back = Math.min(back, lines.length - 1);
    show(lines[lines.length - 1 - back]);
  }

  function close() {
    list.textContent = "";
  }

  function offer(matches) {
    list.textContent = "";
    matches.forEach(function (match) {
      var item = document.createElement("li");
      // textContent, never markup: these are file names from the solver's repo.
      item.textContent = match;
      list.appendChild(item);
    });
  }

  function complete() {
    var caret = input.selectionStart;
    var before = input.value.slice(0, caret);
    var after = input.value.slice(caret);
    var asked = typed;
    return fetch(url + "?line=" + encodeURIComponent(before), {
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (answer) {
        if (answer === null || asked !== typed) {
          return;
        }
        if (answer.line !== before) {
          input.value = answer.line + after;
          input.setSelectionRange(answer.line.length, answer.line.length);
          close();
        } else if (answer.matches.length > 1) {
          offer(answer.matches);
        }
      })
      .catch(function () {
        // A Tab that did nothing; the next command will say if the server is down.
      });
  }

  input.addEventListener("keydown", function (event) {
    if (event.key === "Tab" && !event.shiftKey && input.value.trim() !== "") {
      event.preventDefault();
      complete();
      return;
    }
    if (event.key === "ArrowUp" || event.key === "ArrowDown") {
      event.preventDefault();
      recall(event.key === "ArrowUp" ? -1 : 1);
      return;
    }
    if (event.key === "Escape") {
      close();
    }
  });

  input.addEventListener("input", function () {
    typed += 1;
    back = null;
    close();
  });

  // The form resets after a command reaches the server; the next Up starts
  // from the line just run.
  input.form.addEventListener("reset", function () {
    typed += 1;
    back = null;
    draft = "";
    close();
  });
})();

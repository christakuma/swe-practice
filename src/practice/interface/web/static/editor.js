/*
 * The one editor. Every page that edits code -- a kata, a SQL drill, a
 * container file, a quiz's fix question -- draws it with this file, and no page
 * loads any other editor engine (ADR 0034, which supersedes ADR 0010).
 *
 * **A textarea is the contract, Monaco is an upgrade over it.** A template
 * renders `<textarea data-code-editor="python">` through the
 * `partials/code-editor.html` macro; this file hides it, mounts Monaco beside
 * it, and keeps the two equal on every change. Three things follow, and they
 * are why it is built this way round and not as "Monaco, or a fallback":
 *
 *   - A form that serialises the textarea (the quiz's, through htmx) needs no
 *     script to hand the editor's value over. It is already there.
 *   - If Monaco cannot load, the textarea is simply still on the page, and
 *     submit, Run and the rest keep working on it. CodeMirror failed silently
 *     into exactly this state; this one does it on purpose.
 *   - The handle the workbench's own script holds -- `getValue()` / `setValue()`
 *     -- exists the moment the page does, *before* the 4 MB of Monaco has
 *     arrived, and answers from the textarea until then. Nothing waits.
 *
 * **Monaco is fetched only if a textarea asks for it**, so the index, the
 * browse page and a git scenario never download it.
 *
 * Everything is same-origin: the loader, the core, the worker and the icon font
 * come from `data-monaco` on this file's own <script> tag, which the layout
 * points into the hash-pinned `static/vendor/monaco/vs`.
 */
(function () {
  "use strict";

  var script = document.currentScript;
  var base = new URL(script.getAttribute("data-monaco"), document.baseURI).href;

  var FONT_KEY = "practice.editor.fontSize";
  var FONT_MIN = 11;
  var FONT_MAX = 28;
  var FONT_DEFAULT = 14;

  var handles = [];
  var monacoReady = null;

  // ---- font size, remembered ----------------------------------------------

  // `localStorage` throws in a private window and when storage is blocked, and
  // a font preference is not worth a broken editor: fall back to the default.
  function readFontSize() {
    try {
      var stored = parseInt(window.localStorage.getItem(FONT_KEY), 10);
      if (stored >= FONT_MIN && stored <= FONT_MAX) {
        return stored;
      }
    } catch (error) {
      // fall through to the default
    }
    return FONT_DEFAULT;
  }

  var fontSize = readFontSize();

  function changeFontSize(delta) {
    fontSize = Math.min(FONT_MAX, Math.max(FONT_MIN, fontSize + delta));
    try {
      window.localStorage.setItem(FONT_KEY, String(fontSize));
    } catch (error) {
      // the size still applies for this page
    }
    handles.forEach(function (handle) {
      handle.applyFontSize();
    });
  }

  // ---- the theme, drawn from the app's own colour tokens ------------------

  function token(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  // `app.css` switches on `prefers-color-scheme`, so that is what decides which
  // Monaco base to inherit. The `data-theme` attribute on <html> is not read:
  // it says "dark" on every page and the stylesheet does not use it.
  function prefersLight() {
    return window.matchMedia("(prefers-color-scheme: light)").matches;
  }

  // Monaco wants `rrggbb` for a token and `#rrggbb[aa]` for a UI colour, and
  // the tokens are `#rrggbb`, so both are slices of one string.
  function bare(colour) {
    return colour.replace("#", "");
  }

  function defineTheme(monaco) {
    var accent = token("--accent");
    var ink = token("--ink");
    var dim = token("--ink-dim");
    var line = token("--line");
    var sunken = token("--bg-sunken");
    var raised = token("--bg-raised");
    monaco.editor.defineTheme("practice", {
      base: prefersLight() ? "vs" : "vs-dark",
      inherit: true,
      rules: [
        { token: "", foreground: bare(ink) },
        { token: "comment", foreground: bare(dim), fontStyle: "italic" },
        { token: "keyword", foreground: bare(accent) },
        { token: "string", foreground: bare(token("--pass")) },
        { token: "number", foreground: bare(token("--note")) },
        { token: "type", foreground: bare(token("--note")) },
        { token: "operator", foreground: bare(ink) },
        { token: "delimiter", foreground: bare(dim) },
        { token: "predefined", foreground: bare(accent) }
      ],
      colors: {
        "editor.background": sunken,
        "editor.foreground": ink,
        "editorLineNumber.foreground": dim,
        "editorLineNumber.activeForeground": ink,
        "editor.lineHighlightBackground": raised,
        "editor.lineHighlightBorder": raised,
        "editorCursor.foreground": accent,
        "editor.selectionBackground": accent + "44",
        "editor.inactiveSelectionBackground": accent + "22",
        "editorIndentGuide.background1": line,
        "editorIndentGuide.activeBackground1": dim,
        "editorWidget.background": raised,
        "editorWidget.border": line,
        "editorBracketMatch.background": accent + "33",
        "editorBracketMatch.border": accent,
        "scrollbarSlider.background": line + "99",
        "focusBorder": accent
      }
    });
  }

  // ---- loading Monaco ------------------------------------------------------

  // A web worker cannot be started from a cross-origin or relative script URL
  // it cannot resolve, so the worker is a one-line data: script that sets the
  // base URL and imports Monaco's. Absolute URLs, because a data: document has
  // no location to resolve a relative one against.
  function workerUrl() {
    var body =
      "self.MonacoEnvironment = { baseUrl: " + JSON.stringify(base + "/../") + " };" +
      "importScripts(" + JSON.stringify(base + "/base/worker/workerMain.js") + ");";
    return "data:text/javascript;charset=utf-8," + encodeURIComponent(body);
  }

  function loadMonaco() {
    if (monacoReady !== null) {
      return monacoReady;
    }
    monacoReady = new Promise(function (resolve, reject) {
      var loader = document.createElement("script");
      loader.src = base + "/loader.js";
      loader.onerror = function () {
        reject(new Error("Monaco's loader did not load"));
      };
      loader.onload = function () {
        window.MonacoEnvironment = {
          getWorkerUrl: function () {
            return workerUrl();
          }
        };
        window.require.config({ paths: { vs: base } });
        window.require(["vs/editor/editor.main"], function () {
          defineTheme(window.monaco);
          // The OS theme can change while the page is open.
          window.matchMedia("(prefers-color-scheme: light)").addEventListener(
            "change",
            function () {
              defineTheme(window.monaco);
              window.monaco.editor.setTheme("practice");
            }
          );
          resolve(window.monaco);
        }, reject);
      };
      document.head.appendChild(loader);
    });
    return monacoReady;
  }

  // ---- one editor ----------------------------------------------------------

  function mount(area) {
    var language = area.getAttribute("data-code-editor") || "plaintext";
    var wrapper = area.closest(".code-editor");
    var runSelector = area.getAttribute("data-run");
    var editor = null;
    var readOnly = false;

    // LF always. Monaco defaults a new model's line ending to the platform's,
    // so on Windows a solution would be submitted with CRLF -- and the textarea,
    // which normalises to LF, would disagree with the document it mirrors. Found
    // by typing into it in a browser. The graded source, the stub and every
    // fixture in this repository are LF (`.gitattributes`).
    function text() {
      return editor.getValue({ lineEnding: "\n", preserveBOM: false });
    }

    var handle = {
      textarea: area,
      getValue: function () {
        return editor === null ? area.value : text();
      },
      setValue: function (value) {
        area.value = value;
        if (editor !== null && text() !== value) {
          editor.setValue(value);
        }
      },
      // Own-editor mode makes this one a mirror of a file, and a mirror has to
      // stop looking editable: no caret, and no typing that would be overwritten
      // by the next save.
      setReadOnly: function (value) {
        readOnly = value;
        area.readOnly = value;
        if (editor !== null) {
          editor.updateOptions({ readOnly: value });
        }
      },
      focus: function () {
        if (editor !== null) {
          editor.focus();
        } else {
          area.focus();
        }
      },
      applyFontSize: function () {
        if (editor !== null) {
          editor.updateOptions({ fontSize: fontSize });
        }
      },
      dispose: function () {
        if (editor !== null) {
          editor.dispose();
          editor = null;
        }
      }
    };

    // Ctrl+Enter clicks whatever button `data-run` names. Clicking it, rather
    // than calling its handler, means a disabled button -- one already running
    // -- ignores the shortcut for the same reason it ignores the mouse.
    function run() {
      var button = runSelector ? document.querySelector(runSelector) : null;
      if (button !== null && !button.disabled) {
        button.click();
      }
    }

    loadMonaco().then(function (monaco) {
      if (!area.isConnected) {
        return; // swapped out while Monaco was loading
      }
      var host = document.createElement("div");
      host.className = "code-editor-host";
      area.insertAdjacentElement("afterend", host);

      editor = monaco.editor.create(host, {
        value: area.value,
        language: language,
        theme: "practice",
        readOnly: readOnly,
        fontFamily: token("--mono"),
        fontSize: fontSize,
        automaticLayout: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        padding: { top: 8, bottom: 8 },
        // Four spaces everywhere but YAML, where two is the convention a
        // compose file is read in. `detectIndentation` off, so a stub that
        // happens to be indented with two does not change what Tab does.
        tabSize: language === "yaml" ? 2 : 4,
        insertSpaces: true,
        detectIndentation: false,
        autoIndent: "full",
        autoClosingBrackets: "always",
        autoClosingQuotes: "always",
        autoSurround: "languageDefined",
        matchBrackets: "always",
        bracketPairColorization: { enabled: true },
        renderWhitespace: "selection",
        // Practice, not an IDE: completion would answer the question the
        // exercise is asking. Find, bracket matching and Ctrl+/ stay.
        quickSuggestions: false,
        suggestOnTriggerCharacters: false,
        wordBasedSuggestions: "off",
        parameterHints: { enabled: false },
        acceptSuggestionOnEnter: "off",
        tabCompletion: "off",
        fixedOverflowWidgets: true
      });

      editor.getModel().setEOL(monaco.editor.EndOfLineSequence.LF);

      // The textarea follows the document on every change, which is the whole
      // reason a plain form can serialise it.
      editor.onDidChangeModelContent(function () {
        area.value = text();
      });

      editor.addCommand(
        monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
        run
      );

      area.hidden = true;
      if (wrapper !== null) {
        wrapper.classList.add("is-monaco");
      }
    }).catch(function (error) {
      // The textarea is still there, so this is a degraded editor and not a
      // broken page. Said in the console and on the page, not swallowed.
      console.error(error);
      if (wrapper !== null) {
        wrapper.classList.add("is-plain");
      }
    });

    handles.push(handle);
    return handle;
  }

  // A swap removes the textarea and its host but not the Monaco editor behind
  // them, which stays reachable through `handles`; dispose what is detached.
  function sweep() {
    handles = handles.filter(function (handle) {
      if (handle.textarea.isConnected) {
        return true;
      }
      handle.dispose();
      return false;
    });
  }

  function mountAll(root) {
    sweep();
    root.querySelectorAll("textarea[data-code-editor]").forEach(function (area) {
      if (area.getAttribute("data-mounted") !== null) {
        return;
      }
      area.setAttribute("data-mounted", "");
      var handle = mount(area);
      // The workbench's own script holds this one by name.
      if (area.id === "source") {
        window.practiceEditor = handle;
      }
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-editor-font]");
    if (button !== null) {
      changeFontSize(parseInt(button.getAttribute("data-editor-font"), 10));
    }
  });

  // htmx swaps in fragments, and a fragment can carry an editor. `htmx:load`
  // fires for the initial page too, which is why there is no separate call.
  document.addEventListener("htmx:load", function (event) {
    mountAll(event.target);
  });
  mountAll(document);
})();

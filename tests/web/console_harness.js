// Runs `static/console.js` against a scripted console, for
// `test_console_script.py`. Not a browser: an input, a transcript, a list and
// a `fetch` that answers what it was last told to, and nothing else.
//
//   node console_harness.js <script> <url> <case as JSON>
//
// The case is {lines, steps}. `lines` is the transcript the page loaded with;
// each step is one of
//   ["key", name]      a keydown, with Shift if the name is "Shift+Tab"
//   ["type", text]     the input now holds `text`, caret at the end
//   ["caret", n]       the caret moves to `n`
//   ["answer", body]   what the next completion request answers
//   ["tab-then", step]  Tab, then `step` before the answer lands
//   ["ran", line]      a command reached the server: the transcript gains the
//                      line and the form resets, as htmx does
// Prints one {value, listed, prevented, asked} per step.
const fs = require("fs");
const vm = require("vm");

const [script, url, raw] = process.argv.slice(2);
const scenario = JSON.parse(raw);

function target(extra) {
  const listeners = {};
  return Object.assign(
    {
      addEventListener(type, fn) {
        (listeners[type] = listeners[type] || []).push(fn);
      },
      fire(type, event) {
        (listeners[type] || []).forEach((fn) => fn(event || {}));
      },
    },
    extra
  );
}

const form = target({});
const input = target({
  value: "",
  selectionStart: 0,
  form: form,
  setSelectionRange(start) {
    this.selectionStart = start;
  },
});
const list = {
  items: [],
  set textContent(value) {
    this.items = [];
  },
  appendChild(item) {
    this.items.push(item.textContent);
  },
};

const transcript = scenario.lines.slice();
const document = {
  currentScript: {
    getAttribute: (name) => (name === "data-complete-url" ? url : null),
  },
  querySelector: (selector) =>
    selector === ".console-form input[name=line]" ? input : null,
  getElementById: (id) => (id === "console-completions" ? list : null),
  querySelectorAll: (selector) =>
    selector === "#console-log .entry .line"
      ? transcript.map((line) => ({ textContent: "$ " + line }))
      : [],
  createElement: () => ({ textContent: "" }),
};

let answer = null;
const asked = [];
function fetch(to) {
  asked.push(decodeURIComponent(to.split("?line=")[1] || ""));
  const body = answer;
  return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
}

const settle = () => new Promise((resolve) => setImmediate(resolve));

vm.runInNewContext(fs.readFileSync(script, "utf8"), {
  document,
  fetch,
  encodeURIComponent,
});

// One step, synchronously. Returns whether a keydown was prevented.
function apply(what, value) {
  let prevented = false;
  if (what === "key") {
    input.fire("keydown", {
      key: value === "Shift+Tab" ? "Tab" : value,
      shiftKey: value === "Shift+Tab",
      preventDefault() {
        prevented = true;
      },
    });
  } else if (what === "tab-then") {
    // Tab, and another step before the answer has had a chance to land.
    apply("key", "Tab");
    apply(value[0], value[1]);
  } else if (what === "type") {
    input.value = value;
    input.selectionStart = value.length;
    input.fire("input");
  } else if (what === "caret") {
    input.selectionStart = value;
  } else if (what === "answer") {
    answer = value;
  } else if (what === "ran") {
    transcript.push(value);
    input.value = "";
    form.fire("reset");
  }
  return prevented;
}

(async () => {
  const out = [];
  for (const [what, value] of scenario.steps) {
    const prevented = apply(what, value);
    await settle();
    await settle();
    out.push({
      value: input.value,
      listed: list.items.length ? list.items : null,
      prevented,
      asked: asked.slice(),
    });
  }
  process.stdout.write(JSON.stringify(out));
})();

// Runs `static/editor.js` against a scripted document, for
// `test_editor_script.py`. Not a browser: a textarea that is an object, a
// `<script>` element whose load or failure the scenario decides, and a stand-in
// for Monaco that records what it was asked for. What this can say is what the
// script *configures* and how its handle behaves; typing in a real editor is
// what the browser session recorded in PLAN.md section 16 is for.
//
//   node editor_harness.js <script> <scenario>
//
// Prints one JSON object describing what happened.
const fs = require("fs");
const vm = require("vm");

const [script, scenario] = process.argv.slice(2);

function listeners() {
  const table = {};
  return {
    addEventListener(type, fn) {
      (table[type] = table[type] || []).push(fn);
    },
    fire(type, event) {
      (table[type] = table[type] || []).forEach((fn) => fn(event));
    },
  };
}

const classes = new Set();
const wrapper = { classList: { add: (name) => classes.add(name) } };
const textarea = {
  value: "def f():\n    pass\n",
  hidden: false,
  readOnly: false,
  id: scenario === "other-id" ? "other" : "source",
  attrs: {
    "data-code-editor": scenario === "yaml" ? "yaml" : "python",
    "data-run": "#run",
  },
  getAttribute(name) {
    return name in this.attrs ? this.attrs[name] : null;
  },
  setAttribute(name, value) {
    this.attrs[name] = value;
  },
  closest: () => wrapper,
  insertAdjacentElement: () => {},
  focus() {},
};

let clicked = 0;
const runButton = { disabled: false, click: () => (clicked += 1) };

const store = {};
const storage =
  scenario === "no-storage"
    ? {
        getItem() {
          throw new Error("blocked");
        },
        setItem() {
          throw new Error("blocked");
        },
      }
    : {
        getItem: (key) => (key in store ? store[key] : null),
        setItem: (key, value) => (store[key] = String(value)),
      };
if (scenario === "stored-size") store["practice.editor.fontSize"] = "18";

const doc = Object.assign(listeners(), {
  currentScript: { getAttribute: () => "/static/vendor/monaco/vs" },
  baseURI: "http://localhost/attempt/x",
  querySelectorAll: () => [textarea],
  querySelector: (selector) => (selector === "#run" ? runButton : null),
  createElement: () => ({}),
  documentElement: {},
  head: {
    appendChild(loader) {
      // The scenario decides whether the loader arrives.
      setTimeout(
        () => (scenario === "loader-fails" ? loader.onerror() : loader.onload()),
        0
      );
    },
  },
});

const created = [];
const commands = [];
const fakeEditor = {
  value: "",
  getValue(options) {
    this.lastOptions = options;
    return this.value;
  },
  setValue(value) {
    this.value = value;
  },
  updateOptions(options) {
    created.push({ updated: options });
  },
  onDidChangeModelContent(fn) {
    this.changed = fn;
  },
  addCommand(keys, fn) {
    commands.push([keys, fn]);
  },
  getModel: () => ({ setEOL: (eol) => (fakeEditor.eol = eol) }),
  focus() {},
};
const monaco = {
  KeyMod: { CtrlCmd: 2048 },
  KeyCode: { Enter: 3 },
  editor: {
    EndOfLineSequence: { LF: 0 },
    defineTheme() {},
    setTheme() {},
    create(host, options) {
      fakeEditor.value = options.value;
      created.push({ options });
      return fakeEditor;
    },
  },
};

const window = Object.assign(listeners(), {
  localStorage: storage,
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  require: Object.assign(
    (modules, done) => {
      window.monaco = monaco;
      done();
    },
    { config() {} }
  ),
});

const context = {
  window,
  document: doc,
  URL,
  JSON,
  console: { error() {} },
  setTimeout,
  parseInt,
  encodeURIComponent,
  Math,
  String,
  Promise,
  Error,
  getComputedStyle: () => ({ getPropertyValue: () => "#123456" }),
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(script, "utf8"), context);

(async () => {
  const handle = window.practiceEditor;
  const out = { hasHandle: Boolean(handle) };
  if (handle) {
    out.beforeReady = handle.getValue();
    handle.setValue("x = 1\n");
    out.textareaAfterSet = textarea.value;
  }
  await new Promise((resolve) => setTimeout(resolve, 20));
  out.classes = [...classes];
  out.textareaHidden = textarea.hidden;
  const made = created.find((entry) => entry.options);
  out.options = made ? made.options : null;
  if (made && handle) {
    fakeEditor.value = "typed";
    fakeEditor.changed();
    out.textareaFollows = textarea.value;
    out.lineEnding = fakeEditor.lastOptions && fakeEditor.lastOptions.lineEnding;
    out.eol = fakeEditor.eol;
    handle.setReadOnly(true);
    out.readOnlyApplied = created.some(
      (entry) => entry.updated && entry.updated.readOnly === true
    );
    commands[0][1]();
    runButton.disabled = true;
    commands[0][1]();
    out.runClicks = clicked;
    out.commandKeys = commands[0][0];
    // The font buttons are delegated from the document.
    const press = (delta) =>
      doc.fire("click", {
        target: { closest: () => ({ getAttribute: () => String(delta) }) },
      });
    for (let i = 0; i < 40; i += 1) press(1);
    const sized = created.filter((entry) => entry.updated && entry.updated.fontSize);
    out.fontAfterManyIncreases = sized[sized.length - 1].updated.fontSize;
    out.storedSize = store["practice.editor.fontSize"] || null;
  }
  console.log(JSON.stringify(out));
})();

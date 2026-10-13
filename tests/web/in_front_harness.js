// Runs `static/in-front.js` against a scripted document, for
// `test_in_front_script.py`. Not a browser and not trying to be one: a
// document and a window that are nothing but listeners and one property, a
// `fetch` that records and answers as it was last told to, and a loop that
// lets each step's promises settle before counting.
//
//   node in_front_harness.js <script> <visible|hidden> <url> <steps as JSON>
//
// Prints {counts, posts, unhandled}: the number of requests made after the
// load and after each step, every request, and any rejection nothing caught.
const fs = require("fs");
const vm = require("vm");

const [script, visibility, url, steps] = process.argv.slice(2);

function target(extra) {
  const listeners = {};
  return Object.assign(
    {
      addEventListener(type, fn) {
        (listeners[type] = listeners[type] || []).push(fn);
      },
      removeEventListener(type, fn) {
        listeners[type] = (listeners[type] || []).filter((other) => other !== fn);
      },
      fire(type, event) {
        (listeners[type] || []).slice().forEach((fn) => fn(event || {}));
      },
    },
    extra
  );
}

const document = target({
  visibilityState: visibility,
  currentScript: {
    getAttribute: (name) => (name === "data-current-url" ? url : null),
  },
});
const window = target({});

const posts = [];
let answer = 204;
function fetch(to, options) {
  posts.push([to, options.method]);
  return answer === "down"
    ? Promise.reject(new TypeError("Failed to fetch"))
    : Promise.resolve({ status: answer, ok: answer < 300 });
}

const unhandled = [];
process.on("unhandledRejection", (reason) => unhandled.push(String(reason)));

const settle = () => new Promise((resolve) => setImmediate(resolve));

function play(what, value) {
  if (what === "answer") {
    answer = value;
  } else if (what === "visibility") {
    document.visibilityState = value;
    document.fire("visibilitychange");
  } else if (what === "pageshow") {
    window.fire("pageshow", { persisted: value });
  } else {
    window.fire(what);
  }
}

(async () => {
  const counts = [];
  vm.runInNewContext(fs.readFileSync(script, "utf8"), { document, window, fetch });
  await settle();
  counts.push(posts.length);
  for (const [what, value] of JSON.parse(steps)) {
    play(what, value);
    await settle();
    counts.push(posts.length);
  }
  await settle();
  console.log(JSON.stringify({ counts, posts, unhandled }));
})();

// Tell the server which attempt is in front of the solver (ADR 0026).
//
// With two attempts in two tabs the server sees no request when you switch
// between them, so each open workbench says so itself: once when it loads, if
// it is visible, and again each time it comes back to the front. A tab opened
// in the background says nothing until it is looked at.
//
// A file rather than a few lines in the template, which is where it started,
// because it has behaviour worth running: `tests/web/test_in_front_script.py`
// executes this under node with a scripted document. Inline, the only thing a
// test could do was find its text in the page -- and the first version passed
// that while missing the back button entirely.
//
// Four events, and each is here for a case the others miss:
//
//   visibilitychange  the tab is switched to, or away from
//   focus / blur      the *window* is, with the tab visible throughout: two
//                     windows side by side, or coming back from a chat window
//                     or a terminal, where `practice resume` may have moved
//                     the mark in the meantime
//   pageshow          the page is restored from the back/forward cache, which
//                     reruns no script and changes neither of the above
//
// Switching tabs fires two of them, so `reported` holds one report per time in
// front: set when it is sent, cleared when the page stops being in front.
(function () {
  var url = document.currentScript.getAttribute("data-current-url");
  var reported = false;
  // The attempt was finished, here or in another tab, or it is gone. Nothing
  // this page says from then on can be true, so it stops saying it rather than
  // collecting a refusal every time the tab is looked at. One flag rather than
  // four listeners taken off again: there is one place it can be forgotten.
  var refused = false;

  function away() {
    reported = false;
  }

  function inFront() {
    if (refused || reported || document.visibilityState !== "visible") {
      return;
    }
    reported = true;
    fetch(url, { method: "POST", keepalive: true }).then(
      function (response) {
        refused = response.status === 404 || response.status === 409;
      },
      // The server is not there. Not an error worth a console line on every
      // return to the tab; the next time in front tries again.
      away
    );
  }

  function onVisibility() {
    if (document.visibilityState === "visible") {
      inFront();
    } else {
      away();
    }
  }

  function onShow(event) {
    if (event.persisted) {
      away();
      inFront();
    }
  }

  document.addEventListener("visibilitychange", onVisibility);
  window.addEventListener("focus", inFront);
  window.addEventListener("blur", away);
  window.addEventListener("pageshow", onShow);
  inFront();
})();

# Sequential awaits, fan-out, and a budget for what is optional

## Reading the trace

Each span starts where the one before it ended. Four services that do not
need each other's answers are called as a chain, so the page costs the
**sum** of their latencies. In `async` code this is easy to write by
accident: `await` reads like an ordinary function call, and it is one that
suspends until the result is back. Four `await`s in a row is four waits in
a row.

## Concurrency turns a sum into a maximum

Start every call, then wait for them together (`asyncio.gather`, a
`TaskGroup`, `Promise.all`, an `errgroup` in Go). The page now costs the
**slowest** call, about a second, and the others finish in its shadow.

The catch is that the slowest call is now the page. Fan-out makes this
worse as it grows: if each call is past its p99 one time in a hundred, a
page that waits for four of them meets a slow one on about 4% of requests,
and a page that waits for a hundred meets one on most. This is the argument
of Dean and Barroso's *The Tail at Scale*: at high fan-out, the tail of the
parts is the median of the whole.

## The optional widget gets a budget

Recommendations can be left out, so give them a deadline of their own (300
ms here) and draw the page without them if it passes. Two details:

- **Only the optional call.** A budget on every call drops orders, which
  takes 400 ms, on most requests. Required widgets are waited for, and their
  errors reach the caller rather than becoming a blank panel.
- **Cancel what you stop waiting for.** `asyncio.wait_for` and
  `asyncio.timeout` cancel the call; `asyncio.wait(timeout=...)` does not,
  and leaves it running. At a few hundred requests a second, calls that keep
  going for eight seconds after their page has gone are thousands of
  connections held for nothing.

The panel can still be filled in later, by the browser asking for it on its
own, which is the usual next step for widgets below the fold.

## Testing it without a stopwatch

Timing-based tests of concurrency are slow and flaky. The hidden tests here
check *who has arrived*: every fake service waits at one event until all
four calls have started, so a sequential handler never starts the second
and fails on a guard timeout. A timeout is tested with a service that never
answers, so nothing depends on a deadline firing at a precise moment.

# A five-second network blip became a forty-minute outage: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

one-tap-becomes: two-hundred-fifty-six
why-it-stayed-down: retries-kept-it-overloaded
what-stops-it: retry-in-one-layer, jittered-backoff, retry-budget
what-to-retry: not-processed-yet

## write-the-policy

```python
class Unavailable(Exception):
    """The database could not be reached. The call did not happen."""


ATTEMPTS = 4


def call_with_retries(operation, *, sleep, rng):
    for attempt in range(1, ATTEMPTS):
        try:
            return operation()
        except Unavailable:
            # Full jitter: anywhere between nothing and a ceiling that
            # doubles, so clients that failed together do not retry together.
            sleep(rng.uniform(0, 0.1 * 2**attempt))
    # The last attempt: whatever it raises, the caller gets.
    return operation()
```

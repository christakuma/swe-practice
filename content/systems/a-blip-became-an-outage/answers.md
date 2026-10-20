# A five-second network blip became a forty-minute outage: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

one-tap-becomes:
why-it-stayed-down:
what-stops-it:
what-to-retry:

## write-the-policy

```python
class Unavailable(Exception):
    """The database could not be reached. The call did not happen."""


ATTEMPTS = 5


def call_with_retries(operation, *, sleep, rng):
    # Today's policy: five attempts, any error, no wait.
    for _ in range(1, ATTEMPTS):
        try:
            return operation()
        except Exception:
            continue
    return operation()
```

# Oversold on launch day: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

the-stale-write: 11
why-the-lock-did-not-help: lock-per-process
never-oversell: conditional-decrement, select-for-update, check-constraint
the-hot-key: most-attempts-lose

## reserve-with-a-version

```python
ATTEMPTS = 5


class SoldOut(Exception):
    pass


class Contended(Exception):
    pass


def reserve(store, sku, quantity):
    # Read, decide, and write only if nobody has written since the read. A
    # lost write means another replica got there first, so read again: the
    # stock may now be too low, and that is a decision to make afresh.
    for _ in range(ATTEMPTS):
        item = store.get(sku)
        if item.stock < quantity:
            raise SoldOut(sku)
        left = item.stock - quantity
        if store.put_if_version(sku, left, item.version):
            return left
    raise Contended(sku)
```

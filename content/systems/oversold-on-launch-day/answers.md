# Oversold on launch day: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

the-stale-write:
why-the-lock-did-not-help:
never-oversell:
the-hot-key:

## reserve-with-a-version

```python
import threading


class SoldOut(Exception):
    pass


class Contended(Exception):
    pass


_lock = threading.Lock()


def reserve(store, sku, quantity):
    with _lock:
        item = store.get(sku)
        if item.stock < quantity:
            raise SoldOut(sku)
        store.put(sku, item.stock - quantity)
        return item.stock - quantity
```

# Transfers hang under load, and only a restart clears them: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

which-line-took-it:
which-condition-breaks:
which-fix:
how-to-catch-it:

## fix-the-lock-order

```python
class InsufficientFunds(Exception):
    pass


def transfer(source, target, amount):
    if source is target:
        raise ValueError("cannot transfer to the same account")
    with source.lock:
        with target.lock:
            if source.balance < amount:
                raise InsufficientFunds(source.id)
            source.balance -= amount
            target.balance += amount
```

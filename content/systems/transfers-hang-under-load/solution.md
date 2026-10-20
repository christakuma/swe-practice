# Transfers hang under load, and only a restart clears them: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

which-line-took-it: 8
which-condition-breaks: circular-wait
which-fix: lowest-id-first
how-to-catch-it: lock-order-graph

## fix-the-lock-order

```python
class InsufficientFunds(Exception):
    pass


def transfer(source, target, amount):
    if source is target:
        raise ValueError("cannot transfer to the same account")
    # Lowest id first, whichever way the money moves: every transfer then
    # takes the two locks in one global order, and no cycle of waits can form.
    first, second = sorted((source, target), key=lambda account: account.id)
    with first.lock, second.lock:
        if source.balance < amount:
            raise InsufficientFunds(source.id)
        source.balance -= amount
        target.balance += amount
```

# The order page takes four seconds for big orders: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

what-the-trace-shows:
how-many-queries:
what-about-concurrency:
catch-it-in-ci:

## batch-the-products

```python
def render_order(order_id, db):
    order = db.get_order(order_id)
    lines = []
    for item in db.get_line_items(order_id):
        product = db.get_product(item.product_id)
        lines.append((product.name, item.quantity, product.in_stock))
    return {"order": order.id, "lines": lines}
```

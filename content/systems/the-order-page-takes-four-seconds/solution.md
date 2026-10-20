# The order page takes four seconds for big orders: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

what-the-trace-shows: n-plus-one
how-many-queries: five
what-about-concurrency: four-hundred-ms
catch-it-in-ci: count-the-queries, detect-repeated-queries

## batch-the-products

```python
BATCH = 100


def render_order(order_id, db):
    order = db.get_order(order_id)
    items = db.get_line_items(order_id)
    # Each distinct product once, in the order it first appears, asked for in
    # slices the repository accepts: 2 + ceil(distinct / 100) round trips,
    # however long the order is.
    ids = list(dict.fromkeys(item.product_id for item in items))
    products = {}
    for start in range(0, len(ids), BATCH):
        products.update(db.get_products(ids[start : start + BATCH]))
    lines = []
    for item in items:
        product = products[item.product_id]
        lines.append((product.name, item.quantity, product.in_stock))
    return {"order": order.id, "lines": lines}
```

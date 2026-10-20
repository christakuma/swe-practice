"""Counter-example: batched, and kept in the process so the next render is free."""

BATCH = 100
_PRODUCTS = {}


def render_order(order_id, db):
    order = db.get_order(order_id)
    items = db.get_line_items(order_id)
    missing = [
        product_id
        for product_id in dict.fromkeys(item.product_id for item in items)
        if product_id not in _PRODUCTS
    ]
    for start in range(0, len(missing), BATCH):
        _PRODUCTS.update(db.get_products(missing[start : start + BATCH]))
    lines = []
    for item in items:
        product = _PRODUCTS[item.product_id]
        lines.append((product.name, item.quantity, product.in_stock))
    return {"order": order.id, "lines": lines}

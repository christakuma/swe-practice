"""Counter-example: every distinct product in one call, whatever the limit."""


def render_order(order_id, db):
    order = db.get_order(order_id)
    items = db.get_line_items(order_id)
    ids = list(dict.fromkeys(item.product_id for item in items))
    products = db.get_products(ids) if ids else {}
    lines = []
    for item in items:
        product = products[item.product_id]
        lines.append((product.name, item.quantity, product.in_stock))
    return {"order": order.id, "lines": lines}

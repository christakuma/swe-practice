"""Counter-example: compare-and-set, and a conflict is reported rather than retried."""


class SoldOut(Exception):
    pass


class Contended(Exception):
    pass


def reserve(store, sku, quantity):
    item = store.get(sku)
    if item.stock < quantity:
        raise SoldOut(sku)
    left = item.stock - quantity
    if not store.put_if_version(sku, left, item.version):
        raise Contended(sku)
    return left

"""Counter-example: a conflict is retried, with the version that already lost."""


class SoldOut(Exception):
    pass


class Contended(Exception):
    pass


def reserve(store, sku, quantity):
    item = store.get(sku)
    if item.stock < quantity:
        raise SoldOut(sku)
    left = item.stock - quantity
    for _ in range(5):
        if store.put_if_version(sku, left, item.version):
            return left
    raise Contended(sku)

# The price service falls over at midnight: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

what-happened-at-midnight:
spread-the-expiry:
loads-in-flight:
stale-while-revalidate:

## coalesce-the-misses

```python
TTL_SECONDS = 24 * 60 * 60


class PriceCache:
    def __init__(self, cache, db):
        self.cache = cache
        self.db = db

    async def get(self, product_id):
        price = await self.cache.get(product_id)
        if price is None:
            price = await self.db.load_price(product_id)
            await self.cache.set(product_id, price, ttl=TTL_SECONDS)
        return price
```

# The price service falls over at midnight: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

what-happened-at-midnight: everything-expires-at-once
spread-the-expiry: jittered-ttl
loads-in-flight: twenty
stale-while-revalidate: stale-now

## coalesce-the-misses

```python
import asyncio

TTL_SECONDS = 24 * 60 * 60


class PriceCache:
    def __init__(self, cache, db):
        self.cache = cache
        self.db = db
        self.loading = {}

    async def get(self, product_id):
        price = await self.cache.get(product_id)
        if price is not None:
            return price
        # One load per product in flight: whoever misses first starts it, and
        # everyone who misses while it runs waits for the same result.
        flight = self.loading.get(product_id)
        if flight is None:
            flight = asyncio.ensure_future(self._load(product_id))
            self.loading[product_id] = flight
        return await asyncio.shield(flight)

    async def _load(self, product_id):
        try:
            price = await self.db.load_price(product_id)
            await self.cache.set(product_id, price, ttl=TTL_SECONDS)
            return price
        finally:
            # Forgotten as soon as it lands, success or failure: the cache
            # holds a price, and nothing holds an error.
            del self.loading[product_id]
```

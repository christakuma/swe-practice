# The dashboard waits for everything in turn: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

all-at-once: slowest
the-optional-widget: budget-and-drop
the-fan-out-tail: four-percent
where-the-time-goes: 2

## load-the-widgets-at-once

```python
import asyncio

RECOMMENDATIONS_BUDGET = 0.3


async def optional(call):
    # The one widget the page can do without gets a budget of its own.
    # wait_for cancels the call when the budget runs out, so nothing keeps
    # working for a page that has already been sent.
    try:
        return await asyncio.wait_for(call, RECOMMENDATIONS_BUDGET)
    except Exception:
        return None


async def load_dashboard(user_id, services):
    profile, orders, notifications, recommendations = await asyncio.gather(
        services.profile(user_id),
        services.orders(user_id),
        services.notifications(user_id),
        optional(services.recommendations(user_id)),
    )
    return {
        "profile": profile,
        "orders": orders,
        "notifications": notifications,
        "recommendations": recommendations,
    }
```

# The dashboard waits for everything in turn: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

all-at-once:
the-optional-widget:
the-fan-out-tail:
where-the-time-goes:

## load-the-widgets-at-once

```python
RECOMMENDATIONS_BUDGET = 0.3


async def load_dashboard(user_id, services):
    profile = await services.profile(user_id)
    orders = await services.orders(user_id)
    notifications = await services.notifications(user_id)
    recommendations = await services.recommendations(user_id)
    return {
        "profile": profile,
        "orders": orders,
        "notifications": notifications,
        "recommendations": recommendations,
    }
```

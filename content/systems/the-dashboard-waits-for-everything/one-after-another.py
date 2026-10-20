"""Counter-example: the budget on recommendations, and the calls still in turn."""

import asyncio

RECOMMENDATIONS_BUDGET = 0.3


async def load_dashboard(user_id, services):
    profile = await services.profile(user_id)
    orders = await services.orders(user_id)
    notifications = await services.notifications(user_id)
    try:
        recommendations = await asyncio.wait_for(
            services.recommendations(user_id), RECOMMENDATIONS_BUDGET
        )
    except Exception:
        recommendations = None
    return {
        "profile": profile,
        "orders": orders,
        "notifications": notifications,
        "recommendations": recommendations,
    }

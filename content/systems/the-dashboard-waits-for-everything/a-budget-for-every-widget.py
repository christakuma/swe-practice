"""Counter-example: every widget gets the budget, and any of them may be missing."""

import asyncio

RECOMMENDATIONS_BUDGET = 0.3


async def within_budget(call):
    try:
        return await asyncio.wait_for(call, RECOMMENDATIONS_BUDGET)
    except Exception:
        return None


async def load_dashboard(user_id, services):
    profile, orders, notifications, recommendations = await asyncio.gather(
        within_budget(services.profile(user_id)),
        within_budget(services.orders(user_id)),
        within_budget(services.notifications(user_id)),
        within_budget(services.recommendations(user_id)),
    )
    return {
        "profile": profile,
        "orders": orders,
        "notifications": notifications,
        "recommendations": recommendations,
    }

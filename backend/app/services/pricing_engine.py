# backend/app/services/pricing_engine.py

def calculate_pricing(followers: int, avg_views: int, engagement_rate: float):
    """
    Simple Nigeria-focused pricing logic (V1)
    """

    base_rate_per_view = 2  # ₦2 per view (conservative)
    base_price = avg_views * base_rate_per_view

    engagement_bonus = base_price * engagement_rate

    recommended_price = int(base_price + engagement_bonus)
    minimum_price = int(recommended_price * 0.7)

    return {
        "recommended_price": recommended_price,
        "minimum_price": minimum_price
    }
